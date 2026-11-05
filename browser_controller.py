"""Open / close a Roblox tab when VPN state changes."""

from __future__ import annotations

import threading
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager


class BrowserController:
    def __init__(self, browser: str = "chrome", headless: bool = False) -> None:
        self.browser = (browser or "chrome").lower()
        self.headless = headless
        self._driver: Optional[webdriver.Remote] = None
        self._lock = threading.Lock()
        self._window_handle: Optional[str] = None

    @property
    def is_open(self) -> bool:
        with self._lock:
            return self._driver is not None

    def _build_driver(self):
        if self.browser in ("edge", "msedge"):
            opts = EdgeOptions()
            if self.headless:
                opts.add_argument("--headless=new")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            service = EdgeService(EdgeChromiumDriverManager().install())
            return webdriver.Edge(service=service, options=opts)

        opts = ChromeOptions()
        if self.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_argument("--start-maximized")
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=opts)

    def open_url(self, url: str) -> None:
        with self._lock:
            try:
                if self._driver is None:
                    self._driver = self._build_driver()
                    self._driver.get(url)
                    self._window_handle = self._driver.current_window_handle
                else:
                    # Reuse existing session: focus / navigate dedicated tab
                    try:
                        if self._window_handle and self._window_handle in self._driver.window_handles:
                            self._driver.switch_to.window(self._window_handle)
                            self._driver.get(url)
                        else:
                            self._driver.switch_to.new_window("tab")
                            self._driver.get(url)
                            self._window_handle = self._driver.current_window_handle
                    except WebDriverException:
                        self._safe_quit_unlocked()
                        self._driver = self._build_driver()
                        self._driver.get(url)
                        self._window_handle = self._driver.current_window_handle
            except WebDriverException as exc:
                self._safe_quit_unlocked()
                raise RuntimeError(f"Не удалось открыть браузер: {exc}") from exc

    def close(self) -> None:
        with self._lock:
            self._safe_quit_unlocked()

    def _safe_quit_unlocked(self) -> None:
        if self._driver is None:
            return
        try:
            # Prefer closing only our tracked tab if other tabs exist
            handles = list(self._driver.window_handles)
            if self._window_handle and self._window_handle in handles and len(handles) > 1:
                self._driver.switch_to.window(self._window_handle)
                self._driver.close()
                remaining = self._driver.window_handles
                if remaining:
                    self._driver.switch_to.window(remaining[0])
                    self._driver = None
                    self._window_handle = None
                    return
            self._driver.quit()
        except WebDriverException:
            pass
        finally:
            self._driver = None
            self._window_handle = None
