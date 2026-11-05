"""Detect active VPN connections (adapter up), not merely VPN client processes."""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Iterable

import psutil

# Keywords matched against interface name / description (case-insensitive).
DEFAULT_VPN_KEYWORDS: tuple[str, ...] = (
    "wireguard",
    "wintun",
    "tun",
    "tap-windows",
    "tap adapter",
    "openvpn",
    "nordlynx",
    "nordvpn",
    "mullvad",
    "cloudflare",
    "warp",
    "protonvpn",
    "proton",
    "expressvpn",
    "surfshark",
    "cyberghost",
    "pia",
    "private internet access",
    "anyconnect",
    "cisco vpn",
    "forticlient",
    "globalprotect",
    "palo alto",
    "softether",
    "hamachi",
    "zerotier",
    "tailscale",
    "outline",
    "sing-box",
    "clash",
    "tun2socks",
    "wgp",
    "sstp",
    "l2tp",
    "pptp",
    "ikev2",
    "rasasync",
    "vpn",
)

# Physical / virtual adapters that often contain "tun"/"vpn" but are not user VPNs.
DEFAULT_IGNORE: tuple[str, ...] = (
    "loopback",
    "bluetooth",
    "vethernet",
    "hyper-v",
    "vmware",
    "virtualbox",
    "docker",
    "wsl",
    "xbox",
    "microsoft wi-fi direct",
    "npcap",
    "pseudo-interface",
)


@dataclass(frozen=True)
class VpnAdapter:
    name: str
    description: str
    is_up: bool
    addresses: tuple[str, ...]


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def _matches_any(haystack: str, needles: Iterable[str]) -> bool:
    h = _norm(haystack)
    return any(_norm(n) and _norm(n) in h for n in needles)


def _iface_addresses(addrs) -> tuple[str, ...]:
    out: list[str] = []
    for a in addrs or []:
        if getattr(a, "family", None) is not None and hasattr(a, "address"):
            # Skip IPv6 link-local noise for display
            addr = a.address
            if addr and not addr.startswith("fe80:"):
                out.append(addr)
    return tuple(out)


def list_network_adapters() -> list[VpnAdapter]:
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    result: list[VpnAdapter] = []
    for name, st in stats.items():
        result.append(
            VpnAdapter(
                name=name,
                description=name,
                is_up=bool(st.isup),
                addresses=_iface_addresses(addrs.get(name)),
            )
        )
    return result


def _rasdial_connected() -> list[str]:
    """Return names of connected Windows RAS / built-in VPN links."""
    try:
        completed = subprocess.run(
            ["rasdial"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    text = (completed.stdout or "") + "\n" + (completed.stderr or "")
    if re.search(r"нет подключен|no connections", text, re.I):
        return []

    connected: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.search(
            r"(?:connected to|подключен[оа]?\s+к)\s+(.+?)(?:\.|$)",
            line,
            re.I,
        )
        if m:
            name = m.group(1).strip().strip('"')
            if name:
                connected.append(name)
    return connected


def detect_active_vpns(
    extra_keywords: Iterable[str] | None = None,
    ignore: Iterable[str] | None = None,
) -> list[VpnAdapter]:
    keywords = list(DEFAULT_VPN_KEYWORDS) + list(extra_keywords or [])
    ignores = list(DEFAULT_IGNORE) + list(ignore or [])

    found: list[VpnAdapter] = []
    for adapter in list_network_adapters():
        blob = f"{adapter.name} {adapter.description}"
        if _matches_any(blob, ignores):
            continue
        if not adapter.is_up:
            continue
        if _matches_any(blob, keywords):
            # Require at least one IP when possible — reduces false positives
            # for dormant named adapters that report isup oddly.
            if adapter.addresses or _matches_any(blob, ("wireguard", "wintun", "warp", "nordlynx")):
                found.append(adapter)

    for ras_name in _rasdial_connected():
        found.append(
            VpnAdapter(
                name=f"RAS:{ras_name}",
                description=ras_name,
                is_up=True,
                addresses=(),
            )
        )

    # Deduplicate by name
    uniq: dict[str, VpnAdapter] = {}
    for a in found:
        uniq[a.name] = a
    return list(uniq.values())


class VpnMonitor:
    """Polls for VPN link state and fires callbacks on connect / disconnect."""

    def __init__(
        self,
        poll_interval: float = 1.5,
        extra_keywords: Iterable[str] | None = None,
        ignore: Iterable[str] | None = None,
        on_connect: Callable[[list[VpnAdapter]], None] | None = None,
        on_disconnect: Callable[[], None] | None = None,
        on_tick: Callable[[bool, list[VpnAdapter]], None] | None = None,
    ) -> None:
        self.poll_interval = max(0.4, float(poll_interval))
        self.extra_keywords = list(extra_keywords or [])
        self.ignore = list(ignore or [])
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_tick = on_tick
        self._running = False
        self._was_connected = False

    @property
    def running(self) -> bool:
        return self._running

    def snapshot(self) -> list[VpnAdapter]:
        return detect_active_vpns(self.extra_keywords, self.ignore)

    def start(self) -> None:
        self._running = True
        # Seed state so we don't open a tab for an already-connected VPN
        # unless the UI explicitly asks — initial edge is "no change".
        current = self.snapshot()
        self._was_connected = bool(current)
        if self.on_tick:
            self.on_tick(self._was_connected, current)

    def stop(self) -> None:
        self._running = False

    def poll_once(self) -> tuple[bool, list[VpnAdapter]]:
        adapters = self.snapshot()
        connected = bool(adapters)
        if self.on_tick:
            self.on_tick(connected, adapters)

        if connected and not self._was_connected:
            self._was_connected = True
            if self.on_connect:
                self.on_connect(adapters)
        elif not connected and self._was_connected:
            self._was_connected = False
            if self.on_disconnect:
                self.on_disconnect()

        return connected, adapters

    def run_forever(self, should_continue: Callable[[], bool] | None = None) -> None:
        self.start()
        while self._running and (should_continue is None or should_continue()):
            self.poll_once()
            time.sleep(self.poll_interval)
