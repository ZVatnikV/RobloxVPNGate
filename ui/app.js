const I18N = {
  ru: {
    brand_sub: "Страж подключения",
    nav_dash: "Панель",
    nav_settings: "Настройки",
    nav_adapters: "Адаптеры",
    title_dash: "Панель",
    hint_dash: "Следит за реальным VPN-туннелем, а не за окном клиента",
    title_settings: "Настройки",
    hint_settings: "Подстройте URL, браузер и правила реакции на VPN",
    title_adapters: "Адаптеры",
    hint_adapters: "Список сетевых интерфейсов Windows прямо сейчас",
    refresh: "Обновить",
    start_monitor: "Запустить мониторинг",
    stop_monitor: "Остановить мониторинг",
    meta_vpn: "VPN",
    meta_browser: "Вкладка",
    meta_monitor: "Монитор",
    quick_title: "Быстрые действия",
    quick_hint: "Откройте или закройте Roblox вручную, не дожидаясь смены VPN.",
    open_tab: "Открыть вкладку",
    close_tab: "Закрыть вкладку",
    events: "События",
    active_vpn: "Активные VPN-интерфейсы",
    no_vpn: "VPN не обнаружен",
    set_url: "URL для открытия",
    set_interval: "Интервал опроса (сек)",
    set_browser: "Браузер",
    set_theme: "Тема",
    set_keywords: "Доп. ключевые слова адаптеров (через запятую)",
    set_ignore: "Игнорировать адаптеры (через запятую)",
    set_autostart: "Автозапуск мониторинга",
    set_open: "Открывать вкладку при подключении VPN",
    set_close: "Закрывать вкладку при отключении VPN",
    set_notify: "Показывать события в журнале",
    save: "Сохранить",
    saved: "Сохранено",
    all_adapters: "Все сетевые адаптеры",
    scan: "Сканировать",
    state_idle: "Ожидание",
    state_watch: "Следим",
    state_on: "VPN ON",
    sub_idle: "Мониторинг выключен",
    sub_watch: "Ждём подключение туннеля",
    sub_on: "Туннель активен",
    badge_on: "подключен",
    badge_off: "нет",
    badge_open: "открыта",
    badge_closed: "закрыта",
    badge_mon_on: "вкл",
    badge_mon_off: "выкл",
    up: "UP",
    down: "DOWN",
  },
  en: {
    brand_sub: "Connection guardian",
    nav_dash: "Dashboard",
    nav_settings: "Settings",
    nav_adapters: "Adapters",
    title_dash: "Dashboard",
    hint_dash: "Watches the real VPN tunnel — not just the VPN app window",
    title_settings: "Settings",
    hint_settings: "Tune URL, browser and VPN reaction rules",
    title_adapters: "Adapters",
    hint_adapters: "Live list of Windows network interfaces",
    refresh: "Refresh",
    start_monitor: "Start monitoring",
    stop_monitor: "Stop monitoring",
    meta_vpn: "VPN",
    meta_browser: "Tab",
    meta_monitor: "Monitor",
    quick_title: "Quick actions",
    quick_hint: "Open or close Roblox manually without waiting for VPN changes.",
    open_tab: "Open tab",
    close_tab: "Close tab",
    events: "Events",
    active_vpn: "Active VPN interfaces",
    no_vpn: "No VPN detected",
    set_url: "URL to open",
    set_interval: "Poll interval (sec)",
    set_browser: "Browser",
    set_theme: "Theme",
    set_keywords: "Extra adapter keywords (comma-separated)",
    set_ignore: "Ignore adapters (comma-separated)",
    set_autostart: "Auto-start monitoring",
    set_open: "Open tab when VPN connects",
    set_close: "Close tab when VPN disconnects",
    set_notify: "Show events in the log",
    save: "Save",
    saved: "Saved",
    all_adapters: "All network adapters",
    scan: "Scan",
    state_idle: "Idle",
    state_watch: "Watching",
    state_on: "VPN ON",
    sub_idle: "Monitoring is off",
    sub_watch: "Waiting for a tunnel",
    sub_on: "Tunnel is active",
    badge_on: "connected",
    badge_off: "none",
    badge_open: "open",
    badge_closed: "closed",
    badge_mon_on: "on",
    badge_mon_off: "off",
    up: "UP",
    down: "DOWN",
  },
};

const state = {
  lang: "ru",
  monitoring: false,
  connected: false,
  browserOpen: false,
  notify: true,
};

function t(key) {
  return (I18N[state.lang] && I18N[state.lang][key]) || I18N.ru[key] || key;
}

function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (key) el.textContent = t(key);
  });
  document.getElementById("brandSub").textContent = t("brand_sub");
  const activeView = document.querySelector(".nav-btn.active")?.dataset.view || "dashboard";
  setViewTitles(activeView);
  syncMonitorButton();
  renderStatusBadges();
}

function setViewTitles(view) {
  const map = {
    dashboard: ["title_dash", "hint_dash"],
    settings: ["title_settings", "hint_settings"],
    adapters: ["title_adapters", "hint_adapters"],
  };
  const keys = map[view] || map.dashboard;
  document.getElementById("viewTitle").textContent = t(keys[0]);
  document.getElementById("viewHint").textContent = t(keys[1]);
}

function logEvent(text) {
  if (!state.notify && !text) return;
  const ul = document.getElementById("eventLog");
  const li = document.createElement("li");
  const time = new Date().toLocaleTimeString();
  li.textContent = `${time} — ${text}`;
  ul.prepend(li);
  while (ul.children.length > 40) ul.lastChild.remove();
}

function csvToList(value) {
  return String(value || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function listToCsv(list) {
  return Array.isArray(list) ? list.join(", ") : "";
}

async function api(method, ...args) {
  if (!window.pywebview || !window.pywebview.api || !window.pywebview.api[method]) {
    throw new Error("API unavailable");
  }
  return window.pywebview.api[method](...args);
}

function fillSettings(settings) {
  const form = document.getElementById("settingsForm");
  form.url.value = settings.url || "https://www.roblox.com";
  form.poll_interval_sec.value = settings.poll_interval_sec ?? 1.5;
  form.browser.value = settings.browser || "chrome";
  form.theme.value = settings.theme || "midnight";
  form.custom_adapter_keywords.value = listToCsv(settings.custom_adapter_keywords);
  form.ignore_adapters.value = listToCsv(settings.ignore_adapters);
  form.auto_start_monitor.checked = !!settings.auto_start_monitor;
  form.open_on_connect.checked = !!settings.open_on_connect;
  form.close_on_disconnect.checked = !!settings.close_on_disconnect;
  form.notify_on_change.checked = settings.notify_on_change !== false;
  state.notify = settings.notify_on_change !== false;
  state.lang = settings.language === "en" ? "en" : "ru";
  document.documentElement.dataset.theme = settings.theme || "midnight";
  document.querySelectorAll(".lang-switch button").forEach((b) => {
    b.classList.toggle("active", b.dataset.lang === state.lang);
  });
  applyI18n();
}

function collectSettings() {
  const form = document.getElementById("settingsForm");
  return {
    url: form.url.value.trim(),
    poll_interval_sec: Number(form.poll_interval_sec.value || 1.5),
    browser: form.browser.value,
    theme: form.theme.value,
    custom_adapter_keywords: csvToList(form.custom_adapter_keywords.value),
    ignore_adapters: csvToList(form.ignore_adapters.value),
    auto_start_monitor: form.auto_start_monitor.checked,
    open_on_connect: form.open_on_connect.checked,
    close_on_disconnect: form.close_on_disconnect.checked,
    notify_on_change: form.notify_on_change.checked,
    language: state.lang,
  };
}

function syncMonitorButton() {
  const btn = document.getElementById("btnToggleMonitor");
  btn.textContent = state.monitoring ? t("stop_monitor") : t("start_monitor");
}

function renderStatusBadges() {
  const ring = document.getElementById("statusRing");
  const label = document.getElementById("stateLabel");
  const sub = document.getElementById("stateSub");
  if (state.connected) {
    ring.dataset.state = "connected";
    label.textContent = t("state_on");
    sub.textContent = t("sub_on");
  } else if (state.monitoring) {
    ring.dataset.state = "watching";
    label.textContent = t("state_watch");
    sub.textContent = t("sub_watch");
  } else {
    ring.dataset.state = "idle";
    label.textContent = t("state_idle");
    sub.textContent = t("sub_idle");
  }
  document.getElementById("vpnBadge").textContent = state.connected ? t("badge_on") : t("badge_off");
  document.getElementById("browserBadge").textContent = state.browserOpen ? t("badge_open") : t("badge_closed");
  document.getElementById("monitorBadge").textContent = state.monitoring ? t("badge_mon_on") : t("badge_mon_off");
}

function renderVpnList(adapters) {
  const box = document.getElementById("vpnList");
  const count = document.getElementById("vpnCount");
  const list = adapters || [];
  count.textContent = String(list.length);
  if (!list.length) {
    box.className = "pill-list empty";
    box.innerHTML = `<div class="empty-note">${t("no_vpn")}</div>`;
    return;
  }
  box.className = "pill-list";
  box.innerHTML = list
    .map((a) => {
      const addr = (a.addresses || [])[0] || "";
      return `<div class="pill">${escapeHtml(a.name)}${addr ? ` · ${escapeHtml(addr)}` : ""}</div>`;
    })
    .join("");
}

function renderAdapters(adapters) {
  const root = document.getElementById("adapterTable");
  if (!adapters || !adapters.length) {
    root.innerHTML = `<div class="adapter-row"><div>${t("no_vpn")}</div></div>`;
    return;
  }
  root.innerHTML = adapters
    .map((a) => {
      const st = a.is_up ? `<span class="up">${t("up")}</span>` : `<span class="down">${t("down")}</span>`;
      const addrs = (a.addresses || []).join(", ") || "—";
      return `<div class="adapter-row"><div>${escapeHtml(a.name)}</div><div>${st}</div><div class="addrs">${escapeHtml(addrs)}</div></div>`;
    })
    .join("");
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function applyStatus(payload) {
  if (!payload) return;
  if (typeof payload.connected === "boolean") state.connected = payload.connected;
  if (typeof payload.monitoring === "boolean") state.monitoring = payload.monitoring;
  if (typeof payload.browser_open === "boolean") state.browserOpen = payload.browser_open;
  if (payload.adapters) renderVpnList(payload.adapters);
  syncMonitorButton();
  renderStatusBadges();
}

window.__onNativeEvent = function onNativeEvent(evt) {
  const name = evt?.name;
  const data = evt?.data || {};
  if (name === "status") {
    applyStatus(data);
  } else if (name === "monitor") {
    state.monitoring = !!data.monitoring;
    syncMonitorButton();
    renderStatusBadges();
  } else if (name === "browser") {
    state.browserOpen = !!data.open;
    renderStatusBadges();
    if (state.notify) {
      logEvent(data.open ? (state.lang === "en" ? "Tab opened" : "Вкладка открыта") : (state.lang === "en" ? "Tab closed" : "Вкладка закрыта"));
    }
  } else if (name === "message" && state.notify) {
    logEvent(data.text || "");
  }
};

async function refreshAll() {
  try {
    const status = await api("get_status");
    applyStatus(status);
    if (status.settings) fillSettings(status.settings);
    const adapters = await api("list_adapters");
    renderAdapters(adapters.adapters || []);
    renderVpnList(adapters.vpn || status.adapters || []);
  } catch (err) {
    logEvent(String(err));
  }
}

function wireUi() {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`view-${btn.dataset.view}`).classList.add("active");
      setViewTitles(btn.dataset.view);
    });
  });

  document.querySelectorAll(".lang-switch button").forEach((btn) => {
    btn.addEventListener("click", async () => {
      state.lang = btn.dataset.lang;
      document.querySelectorAll(".lang-switch button").forEach((b) => b.classList.toggle("active", b === btn));
      applyI18n();
      try {
        const payload = collectSettings();
        await api("save_settings", payload);
      } catch (_) {
        /* preview mode */
      }
    });
  });

  document.getElementById("btnToggleMonitor").addEventListener("click", async () => {
    try {
      if (state.monitoring) await api("stop_monitor");
      else await api("start_monitor");
      await refreshAll();
    } catch (err) {
      logEvent(String(err));
    }
  });

  document.getElementById("btnRefresh").addEventListener("click", refreshAll);
  document.getElementById("btnScan").addEventListener("click", refreshAll);

  document.getElementById("btnOpen").addEventListener("click", async () => {
    const res = await api("open_now");
    if (!res.ok) logEvent(res.error || "error");
    await refreshAll();
  });
  document.getElementById("btnClose").addEventListener("click", async () => {
    await api("close_now");
    await refreshAll();
  });

  document.getElementById("settingsForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = collectSettings();
    document.documentElement.dataset.theme = payload.theme;
    state.notify = payload.notify_on_change;
    const res = await api("save_settings", payload);
    const hint = document.getElementById("saveHint");
    hint.textContent = res.ok ? t("saved") : res.error || "error";
    setTimeout(() => { hint.textContent = ""; }, 1800);
    if (res.settings) fillSettings(res.settings);
  });

  document.querySelector('select[name="theme"]').addEventListener("change", (e) => {
    document.documentElement.dataset.theme = e.target.value;
  });
}

function ready(fn) {
  if (window.pywebview) {
    window.addEventListener("pywebviewready", fn);
  } else {
    // Browser preview fallback
    setTimeout(fn, 50);
  }
}

ready(async () => {
  wireUi();
  applyI18n();
  try {
    const settings = await api("get_settings");
    fillSettings(settings);
  } catch (_) {
    fillSettings({
      url: "https://www.roblox.com",
      poll_interval_sec: 1.5,
      browser: "chrome",
      theme: "midnight",
      language: "ru",
      auto_start_monitor: true,
      open_on_connect: true,
      close_on_disconnect: true,
      notify_on_change: true,
      custom_adapter_keywords: [],
      ignore_adapters: [],
    });
    logEvent(state.lang === "en" ? "UI preview mode" : "Режим предпросмотра UI");
  }
  await refreshAll();
});