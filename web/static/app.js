const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor("#ffffff");
  tg.setBackgroundColor("#f7f8fa");
}

const userId = tg?.initDataUnsafe?.user?.id
  || parseInt(new URLSearchParams(location.search).get("user_id") || "0", 10)
  || 0;

const COUNTRIES = [
  ["Afghanistan","AF","93"],["Albania","AL","355"],["Algeria","DZ","213"],["Andorra","AD","376"],
  ["Angola","AO","244"],["Argentina","AR","54"],["Armenia","AM","374"],["Australia","AU","61"],
  ["Austria","AT","43"],["Azerbaijan","AZ","994"],["Bahrain","BH","973"],["Bangladesh","BD","880"],
  ["Belarus","BY","375"],["Belgium","BE","32"],["Brazil","BR","55"],["Bulgaria","BG","359"],
  ["Cambodia","KH","855"],["Canada","CA","1"],["Chile","CL","56"],["China","CN","86"],
  ["Colombia","CO","57"],["Croatia","HR","385"],["Cyprus","CY","357"],["Czech Republic","CZ","420"],
  ["Denmark","DK","45"],["Egypt","EG","20"],["Estonia","EE","372"],["Ethiopia","ET","251"],
  ["Finland","FI","358"],["France","FR","33"],["Georgia","GE","995"],["Germany","DE","49"],
  ["Ghana","GH","233"],["Greece","GR","30"],["Hong Kong","HK","852"],["Hungary","HU","36"],
  ["Iceland","IS","354"],["India","IN","91"],["Indonesia","ID","62"],["Iran","IR","98"],
  ["Iraq","IQ","964"],["Ireland","IE","353"],["Israel","IL","972"],["Italy","IT","39"],
  ["Japan","JP","81"],["Jordan","JO","962"],["Kazakhstan","KZ","7"],["Kenya","KE","254"],
  ["Kuwait","KW","965"],["Kyrgyzstan","KG","996"],["Latvia","LV","371"],["Lebanon","LB","961"],
  ["Libya","LY","218"],["Lithuania","LT","370"],["Luxembourg","LU","352"],["Malaysia","MY","60"],
  ["Maldives","MV","960"],["Mexico","MX","52"],["Moldova","MD","373"],["Morocco","MA","212"],
  ["Myanmar","MM","95"],["Nepal","NP","977"],["Netherlands","NL","31"],["New Zealand","NZ","64"],
  ["Nigeria","NG","234"],["Norway","NO","47"],["Oman","OM","968"],["Pakistan","PK","92"],
  ["Palestine","PS","970"],["Peru","PE","51"],["Philippines","PH","63"],["Poland","PL","48"],
  ["Portugal","PT","351"],["Qatar","QA","974"],["Romania","RO","40"],["Russia","RU","7"],
  ["Saudi Arabia","SA","966"],["Serbia","RS","381"],["Singapore","SG","65"],["Slovakia","SK","421"],
  ["South Africa","ZA","27"],["South Korea","KR","82"],["Spain","ES","34"],["Sri Lanka","LK","94"],
  ["Sweden","SE","46"],["Switzerland","CH","41"],["Syria","SY","963"],["Taiwan","TW","886"],
  ["Tajikistan","TJ","992"],["Tanzania","TZ","255"],["Thailand","TH","66"],["Tunisia","TN","216"],
  ["Turkey","TR","90"],["Turkmenistan","TM","993"],["UAE","AE","971"],["Uganda","UG","256"],
  ["Ukraine","UA","380"],["United Kingdom","GB","44"],["United States","US","1"],
  ["Uzbekistan","UZ","998"],["Venezuela","VE","58"],["Vietnam","VN","84"],["Yemen","YE","967"],
  ["Zambia","ZM","260"],["Zimbabwe","ZW","263"],
];

let currentPhone = "";
let currentPrefix = "91";
let currentTab = "accounts";

function esc(str) {
  return String(str || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function populateCountries() {
  const sel = document.getElementById("country-select");
  sel.innerHTML = "";
  COUNTRIES.forEach(([name, code, dial]) => {
    const opt = document.createElement("option");
    opt.value = dial;
    opt.textContent = `${name} (+${dial})`;
    if (code === "IN") opt.selected = true;
    sel.appendChild(opt);
  });
  updatePrefix();
}

function updatePrefix() {
  const sel = document.getElementById("country-select");
  currentPrefix = sel.value;
  document.getElementById("prefix-display").textContent = "+" + currentPrefix;
}

function showScreen(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

function showMainScreen() {
  showScreen("main-screen");
  if (currentTab === "accounts") loadAccounts();
  else loadStats();
}

function showAddScreen() {
  showScreen("add-screen");
  showStep("step-phone");
  document.getElementById("phone-input").value = "";
  document.getElementById("otp-input").value = "";
  document.getElementById("password-input").value = "";
  document.getElementById("step-2fa").style.display = "none";
}

function goBackToPhone() { showStep("step-phone"); }

function showStep(id) {
  document.querySelectorAll(".step").forEach(s => s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

function showLoader(show) {
  document.getElementById("loader").style.display = show ? "flex" : "none";
}

let _toastTimer;
function showToast(msg, type = "") {
  const el = document.getElementById("toast");
  el.className = "toast";
  el.textContent = msg;
  clearTimeout(_toastTimer);
  requestAnimationFrame(() => {
    el.classList.add("show");
    if (type) el.classList.add(type);
  });
  _toastTimer = setTimeout(() => el.classList.remove("show"), 3200);
}

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
  document.getElementById("tab-" + tab).classList.add("active");
  document.getElementById("tab-content-" + tab).classList.add("active");
  if (tab === "accounts") loadAccounts();
  else loadStats();
}

function buildAccountCard(a) {
  const isActive = a.active !== false;
  const toggleLabel = isActive ? "Deactivate" : "Activate";
  const toggleClass = isActive ? "toggle-btn toggle-active" : "toggle-btn toggle-inactive";
  const statusDot = isActive ? "dot-active" : "dot-inactive";

  return `<div class="account-card${isActive ? "" : " account-inactive"}" id="card-${esc(a.phone)}">
    <div class="account-avatar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
      </svg>
    </div>
    <div class="account-body">
      <div class="account-name-row">
        <span class="account-name">${esc(a.name)}</span>
        <span class="status-dot ${statusDot}"></span>
      </div>
      ${a.username ? `<div class="account-username">@${esc(a.username)}</div>` : ""}
      <div class="account-phone">${esc(a.phone)}</div>
    </div>
    <div class="account-actions">
      <button class="${toggleClass}" onclick="toggleAccount('${esc(a.phone)}', ${isActive})">${toggleLabel}</button>
      <button class="remove-btn" onclick="removeAccount('${esc(a.phone)}')">Remove</button>
    </div>
  </div>`;
}

async function loadAccounts() {
  const list = document.getElementById("accounts-list");
  list.innerHTML = '<div class="skeleton-card"></div><div class="skeleton-card"></div>';

  if (!userId) {
    list.innerHTML = `<div class="empty-state">
      <div class="empty-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg></div>
      <div class="empty-title">No user session</div>
      <div class="empty-sub">Open this panel from the Bumpify bot</div>
    </div>`;
    return;
  }

  try {
    const res = await fetch(`/api/accounts?user_id=${userId}`);
    const data = await res.json();
    if (!data.ok) { showToast(data.error || "Failed to load", "error"); list.innerHTML = ""; return; }
    if (!data.accounts.length) {
      list.innerHTML = `<div class="empty-state">
        <div class="empty-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
        </svg></div>
        <div class="empty-title">No accounts yet</div>
        <div class="empty-sub">Add your first Telegram account below</div>
      </div>`;
      return;
    }
    list.innerHTML = data.accounts.map(buildAccountCard).join("");
  } catch (e) {
    list.innerHTML = `<div class="empty-state"><div class="empty-title">Network error</div><div class="empty-sub">Could not load accounts</div></div>`;
  }
}

async function loadStats() {
  const el = document.getElementById("stats-content");
  el.innerHTML = `<div class="skeleton-card" style="height:96px"></div><div class="skeleton-card" style="height:200px;margin-top:12px;"></div>`;

  if (!userId) {
    el.innerHTML = `<div class="no-data"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg><p>Open this panel from the Bumpify bot to see analytics</p></div>`;
    return;
  }

  try {
    const res = await fetch(`/api/stats?user_id=${userId}`);
    const d = await res.json();
    if (!d.ok) { el.innerHTML = `<div class="no-data"><p>${esc(d.error || "Failed to load stats")}</p></div>`; return; }
    renderStats(el, d);
  } catch (e) {
    el.innerHTML = `<div class="no-data"><p>Network error — could not load analytics</p></div>`;
  }
}

function rateClass(rate) {
  if (rate >= 75) return "good";
  if (rate >= 40) return "mid";
  return "bad";
}

function renderStats(el, d) {
  let html = `<div class="stat-grid">
    <div class="stat-card"><div class="stat-label">Total Sent</div><div class="stat-value">${d.total.toLocaleString()}</div></div>
    <div class="stat-card"><div class="stat-label">Success Rate</div><div class="stat-value blue">${d.rate}%</div></div>
    <div class="stat-card"><div class="stat-label">Successful</div><div class="stat-value green">${d.success.toLocaleString()}</div></div>
    <div class="stat-card"><div class="stat-label">Failed</div><div class="stat-value red">${d.failed.toLocaleString()}</div></div>
  </div>`;

  if (d.per_account && d.per_account.length > 0) {
    html += `<div class="section-title" style="margin-top:4px;">Per Account Performance</div><div class="acc-perf-list">`;
    for (const acc of d.per_account) {
      const rc = rateClass(acc.rate);
      html += `<div class="acc-perf-card">
        <div class="acc-perf-header">
          <div>
            <div class="acc-perf-phone">${esc(acc.phone)}</div>
            <div class="acc-perf-nums">✅ ${acc.success.toLocaleString()}  ❌ ${acc.failed.toLocaleString()}  /  ${acc.total.toLocaleString()} total</div>
          </div>
          <div class="acc-perf-rate">${acc.rate}%</div>
        </div>
        <div class="progress-bg"><div class="progress-bar ${rc}" style="width:${acc.rate}%"></div></div>
      </div>`;
    }
    html += `</div>`;
  }

  if (d.recent && d.recent.length > 0) {
    html += `<div class="section-title" style="margin-top:4px;">Recent Activity</div><div class="recent-list">`;
    for (const r of d.recent.slice(0, 20)) {
      const ok = r.success;
      const link = r.group_username ? `https://t.me/${r.group_username}` : "";
      const titleEl = link
        ? `<a href="${link}" target="_blank" class="recent-group" style="color:var(--accent);text-decoration:none;">${esc(r.group_title || r.group_id)}</a>`
        : `<div class="recent-group">${esc(r.group_title || String(r.group_id))}</div>`;
      html += `<div class="recent-row">
        <div class="recent-dot ${ok ? "ok" : "fail"}"></div>
        <div class="recent-body">
          ${titleEl}
          <div class="recent-meta">${esc(r.account_phone)} · Account #${r.account_num}</div>
          ${!ok && r.error ? `<div class="recent-err">${esc(r.error)}</div>` : ""}
        </div>
      </div>`;
    }
    html += `</div>`;
  } else if (d.total === 0) {
    html += `<div class="no-data" style="margin-top:12px;">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
      <p>No broadcast data yet.<br>Start ads from the bot to see analytics here.</p>
    </div>`;
  }

  el.innerHTML = html;
}

async function toggleAccount(phone, currentlyActive) {
  showLoader(true);
  try {
    const res = await fetch("/api/toggle-account", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, phone }),
    });
    const data = await res.json();
    if (data.ok) {
      showToast(data.active ? "Account activated" : "Account deactivated", "success");
      await loadAccounts();
    } else {
      showToast(data.error || "Toggle failed", "error");
    }
  } catch { showToast("Network error", "error"); }
  finally { showLoader(false); }
}

async function removeAccount(phone) {
  if (!confirm(`Permanently remove ${phone}?`)) return;
  showLoader(true);
  try {
    const res = await fetch("/api/remove-account", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, phone }),
    });
    const data = await res.json();
    if (data.ok) { showToast("Account removed", "success"); await loadAccounts(); }
    else showToast(data.error || "Failed to remove", "error");
  } catch { showToast("Network error", "error"); }
  finally { showLoader(false); }
}

async function sendOtp() {
  if (!userId) { showToast("Open this panel from the Bumpify bot", "error"); return; }
  const rawPhone = document.getElementById("phone-input").value.trim().replace(/\D/g, "");
  if (rawPhone.length < 5) { showToast("Enter a valid phone number", "error"); return; }
  currentPhone = currentPrefix + rawPhone;
  showLoader(true);
  try {
    const res = await fetch("/api/send-otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: currentPhone, user_id: userId }),
    });
    const data = await res.json();
    if (data.ok) {
      showToast("OTP sent successfully", "success");
      showStep("step-otp");
      setTimeout(() => document.getElementById("otp-input").focus(), 100);
    } else {
      showToast(data.error || "Failed to send OTP", "error");
    }
  } catch { showToast("Network error", "error"); }
  finally { showLoader(false); }
}

async function verifyOtp() {
  const code = document.getElementById("otp-input").value.trim();
  const password = document.getElementById("password-input").value.trim();
  if (!code) { showToast("Enter the verification code", "error"); return; }
  showLoader(true);
  try {
    const res = await fetch("/api/verify-otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: currentPhone, user_id: userId, code, password: password || undefined }),
    });
    const data = await res.json();
    if (data.ok) {
      document.getElementById("success-name").textContent = data.name;
      const parts = [];
      if (data.username) parts.push("@" + data.username);
      if (data.tg_user_id) parts.push("ID: " + data.tg_user_id);
      parts.push(data.phone);
      document.getElementById("success-meta").textContent = parts.join("  ·  ");
      showScreen("success-screen");
    } else if (data.error === "2FA_REQUIRED") {
      const fa = document.getElementById("step-2fa");
      fa.style.display = "flex";
      fa.style.flexDirection = "column";
      showToast("Enter your 2FA password below", "");
      setTimeout(() => document.getElementById("password-input").focus(), 100);
    } else {
      showToast(data.error || "Verification failed", "error");
    }
  } catch { showToast("Network error", "error"); }
  finally { showLoader(false); }
}

document.addEventListener("keydown", e => {
  const activeStep = document.querySelector(".step.active");
  if (!activeStep) return;
  if (e.key === "Enter") {
    if (activeStep.id === "step-phone") sendOtp();
    else if (activeStep.id === "step-otp") verifyOtp();
  }
});

populateCountries();
loadAccounts();
