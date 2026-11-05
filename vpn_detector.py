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

# Adapters that stay "up" forever and must not count as the Roblox VPN toggle.
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
    "teredo",
    "isatap",
    "wan miniport",
    "radmin",
    "famatech",
    "hamachi",
    "logmein",
)

# Names that are the normal internet link, not a tunnel.
PHYSICAL_HINTS: tuple[str, ...] = (
    "беспровод",
    "wi-fi",
    "wifi",
    "wireless",
    "ethernet",
    "локальн",
    "tp-link",
    "realtek",
    "intel",
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


def _run_hidden(args: list[str]) -> str:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (completed.stdout or "") + "\n" + (completed.stderr or "")


def _default_route_ips() -> list[tuple[int, str]]:
    """IPv4 default routes as (metric, interface address), lowest metric first."""
    text = _run_hidden(["route", "print", "-4"])
    found: list[tuple[int, str]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0] != "0.0.0.0" or parts[1] != "0.0.0.0":
            continue
        iface_ip = parts[3]
        if not re.match(r"^\d+\.\d+\.\d+\.\d+$", iface_ip):
            continue
        try:
            metric = int(parts[4])
        except ValueError:
            continue
        found.append((metric, iface_ip))
    found.sort(key=lambda item: item[0])
    return found


def _adapter_for_ip(ip: str, adapters: list[VpnAdapter]) -> VpnAdapter | None:
    for adapter in adapters:
        if ip in adapter.addresses:
            return adapter
    return None


def _is_internet_vpn(adapter: VpnAdapter, keywords: list[str], ignores: list[str]) -> bool:
    blob = f"{adapter.name} {adapter.description}"
    if _matches_any(blob, ignores):
        return False
    if _matches_any(blob, keywords):
        return True
    # A non-physical interface that won the default route is a tunnel
    # (happ-tun, sing-tun, outline, amnezia, ...).
    return not _matches_any(blob, PHYSICAL_HINTS)


def detect_active_vpns(
    extra_keywords: Iterable[str] | None = None,
    ignore: Iterable[str] | None = None,
) -> list[VpnAdapter]:
    """VPN is on only when the best default route goes through a tunnel.

    Always-on virtual LANs (Radmin, Hamachi) stay up without owning traffic,
    so adapter-up checks never see a connect/disconnect edge.
    """
    keywords = list(DEFAULT_VPN_KEYWORDS) + list(extra_keywords or [])
    ignores = list(DEFAULT_IGNORE) + list(ignore or [])
    adapters = list_network_adapters()

    for _metric, iface_ip in _default_route_ips():
        winner = _adapter_for_ip(iface_ip, adapters)
        if winner is None or not winner.is_up:
            continue
        if _is_internet_vpn(winner, keywords, ignores):
            return [winner]
        # Best route is ordinary Wi-Fi/Ethernet — tunnel is not carrying traffic.
        return []

    for ras_name in _rasdial_connected():
        return [
            VpnAdapter(
                name=f"RAS:{ras_name}",
                description=ras_name,
                is_up=True,
                addresses=(),
            )
        ]
    return []


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
        current = self.snapshot()
        self._was_connected = False
        if self.on_tick:
            self.on_tick(bool(current), current)
        # If the tunnel is already the default route, open immediately.
        if current and self.on_connect:
            self._was_connected = True
            self.on_connect(current)

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
