"""Roblox VPN Gate — open Roblox when VPN connects, close when it drops."""

from __future__ import annotations

import json
import sys
import threading
import traceback
from pathlib import Path

import webview

from browser_controller import BrowserController
from config import ensure_settings, resource_root, save_settings
from vpn_detector import VpnMonitor, detect_active_vpns, list_network_adapters

UI_DIR = resource_root() / "ui"


class Api:
    def __init__(self) -> None:
        self.settings = ensure_settings()
        self.browser = BrowserController(
            browser=self.settings.get("browser", "chrome"),
            headless=bool(self.settings.get("headless", False)),
        )
        self.monitor: VpnMonitor | None = None
        self._monitor_thread: threading.Thread | None = None
        self._stop_flag = threading.Event()
        self._window: webview.Window | None = None
        self._last_status = {
            "connected": False,
            "adapters": [],
            "monitoring": False,
            "browser_open": False,
            "message": "",
        }
        self._lock = threading.Lock()

    def bind_window(self, window: webview.Window) -> None:
        self._window = window

    def get_settings(self) -> dict:
        return dict(self.settings)

    def save_settings(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return {"ok": False, "error": "invalid payload"}
        self.settings.update(payload)
        save_settings(self.settings)
        # Rebuild browser prefs
        was_open = self.browser.is_open
        if was_open:
            self.browser.close()
        self.browser = BrowserController(
            browser=self.settings.get("browser", "chrome"),
            headless=bool(self.settings.get("headless", False)),
        )
        # Restart monitor with new interval / keywords if running
        if self._last_status["monitoring"]:
            self.stop_monitor()
            self.start_monitor()
        return {"ok": True, "settings": self.settings}

    def get_status(self) -> dict:
        with self._lock:
            status = dict(self._last_status)
        status["browser_open"] = self.browser.is_open
        status["settings"] = self.settings
        return status

    def list_adapters(self) -> dict:
        adapters = [
            {
                "name": a.name,
                "is_up": a.is_up,
                "addresses": list(a.addresses),
            }
            for a in list_network_adapters()
        ]
        vpn = [
            {
                "name": a.name,
                "is_up": a.is_up,
                "addresses": list(a.addresses),
            }
            for a in detect_active_vpns(
                self.settings.get("custom_adapter_keywords") or [],
                self.settings.get("ignore_adapters") or [],
            )
        ]
        return {"adapters": adapters, "vpn": vpn}

    def start_monitor(self) -> dict:
        if self._monitor_thread and self._monitor_thread.is_alive():
            return {"ok": True, "already": True}
        self._stop_flag.clear()
        self.monitor = VpnMonitor(
            poll_interval=float(self.settings.get("poll_interval_sec", 1.5)),
            extra_keywords=self.settings.get("custom_adapter_keywords") or [],
            ignore=self.settings.get("ignore_adapters") or [],
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
            on_tick=self._on_tick,
        )
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self._push_event("monitor", {"monitoring": True})
        return {"ok": True}

    def stop_monitor(self) -> dict:
        self._stop_flag.set()
        if self.monitor:
            self.monitor.stop()
        with self._lock:
            self._last_status["monitoring"] = False
        self._push_event("monitor", {"monitoring": False})
        return {"ok": True}

    def open_now(self) -> dict:
        try:
            self.browser.open_url(self.settings.get("url") or "https://www.roblox.com")
            self._push_event("browser", {"open": True})
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def close_now(self) -> dict:
        self.browser.close()
        self._push_event("browser", {"open": False})
        return {"ok": True}

    def test_vpn_snapshot(self) -> dict:
        return self.list_adapters()

    def _monitor_loop(self) -> None:
        assert self.monitor is not None
        self.monitor.start()
        with self._lock:
            self._last_status["monitoring"] = True
        while not self._stop_flag.is_set():
            try:
                self.monitor.poll_once()
            except Exception:  # noqa: BLE001
                traceback.print_exc()
            self._stop_flag.wait(self.monitor.poll_interval)
        with self._lock:
            self._last_status["monitoring"] = False

    def _on_tick(self, connected: bool, adapters) -> None:
        payload = {
            "connected": connected,
            "adapters": [
                {"name": a.name, "addresses": list(a.addresses)} for a in adapters
            ],
            "monitoring": True,
            "browser_open": self.browser.is_open,
        }
        with self._lock:
            self._last_status.update(payload)
        self._push_event("status", payload)

    def _on_connect(self, adapters) -> None:
        names = ", ".join(a.name for a in adapters) or "VPN"
        self._set_message(f"VPN подключен: {names}")
        if self.settings.get("open_on_connect", True):
            try:
                self.browser.open_url(self.settings.get("url") or "https://www.roblox.com")
                self._push_event("browser", {"open": True, "reason": "vpn_connect"})
            except Exception as exc:  # noqa: BLE001
                self._set_message(f"Ошибка браузера: {exc}")

    def _on_disconnect(self) -> None:
        self._set_message("VPN отключен")
        if self.settings.get("close_on_disconnect", True):
            self.browser.close()
            self._push_event("browser", {"open": False, "reason": "vpn_disconnect"})

    def _set_message(self, text: str) -> None:
        with self._lock:
            self._last_status["message"] = text
        self._push_event("message", {"text": text})

    def _push_event(self, name: str, data: dict) -> None:
        if not self._window:
            return
        try:
            payload = json.dumps({"name": name, "data": data}, ensure_ascii=False)
            self._window.evaluate_js(f"window.__onNativeEvent && window.__onNativeEvent({payload})")
        except Exception:  # noqa: BLE001
            pass


def main() -> int:
    api = Api()
    settings = api.settings
    window = webview.create_window(
        title="Roblox VPN Gate",
        url=(UI_DIR / "index.html").as_uri(),
        js_api=api,
        width=1100,
        height=740,
        min_size=(880, 600),
        background_color="#0B0D12",
        text_select=False,
    )
    api.bind_window(window)

    def on_loaded():
        if settings.get("auto_start_monitor", True):
            api.start_monitor()

    webview.start(on_loaded, debug=False)
    api.stop_monitor()
    api.browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())