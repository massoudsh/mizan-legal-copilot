const form = document.querySelector("#token-form");
const login = document.querySelector("#login");
const dashboard = document.querySelector("#dashboard");
const status = document.querySelector("#login-status");
const actionStatus = document.querySelector("#action-status");
let token = "";
let session = 0;

const escapeHtml = (text) => String(text).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
const labels = { low: "کم", medium: "متوسط", high: "بالا", critical: "بحرانی", open: "باز", in_progress: "در حال انجام", done: "انجام‌شده", overdue: "عقب‌افتاده", pending: "در انتظار بررسی", approved: "تأییدشده", rejected: "ردشده" };

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } });
  if (!response.ok) {
    if (response.status === 401) throw new Error("توکن دسترسی نامعتبر است.");
    if (response.status === 403) throw new Error("اجازهٔ انجام این عملیات را ندارید.");
    if (response.status === 409) throw new Error("وضعیت این مورد تغییر کرده است؛ دوباره بارگذاری کنید.");
    throw new Error("انجام درخواست ممکن نشد. لطفاً دوباره تلاش کنید.");
  }
  return response.json();
}

async function loadDashboard() {
  const currentSession = session;
  const [data, identity, obligations, reviews] = await Promise.all([
    api("/dashboard"), api("/me"), api("/obligations"), api("/reviews"),
  ]);
  if (currentSession !== session) return false;
  const canWrite = ["owner", "admin", "analyst"].includes(identity.role);
  document.querySelector("#decision-count").textContent = data.decision_count.toLocaleString("fa-IR");
  document.querySelector("#critical-count").textContent = data.critical_decision_count.toLocaleString("fa-IR");
  document.querySelector("#alert-count").textContent = data.unread_alert_count.toLocaleString("fa-IR");
  document.querySelector("#risk-distribution").innerHTML = Object.entries(data.risk_distribution).map(([level, count]) => `<div class="risk-row"><span>${escapeHtml(labels[level] || level)}</span><b>${Number(count).toLocaleString("fa-IR")}</b></div>`).join("");
  document.querySelector("#recent-decisions").innerHTML = data.recent_decisions.length ? data.recent_decisions.map((decision) => `<article class="decision-row"><strong>${escapeHtml(decision.title)}</strong><span>${escapeHtml(labels[decision.risk_level])} · ${new Date(decision.created_at).toLocaleDateString("fa-IR")}</span></article>`).join("") : "<p>هنوز تصمیمی ثبت نشده است.</p>";
  document.querySelector("#obligations").innerHTML = obligations.length ? obligations.map((item) => `<article class="decision-row"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.due_on)} · ${escapeHtml(labels[item.status])}</span>${canWrite ? `<label>وضعیت تعهد<select data-obligation="${Number(item.id)}">${["open", "in_progress", "done", "overdue"].map((value) => `<option value="${value}" ${value === item.status ? "selected" : ""}>${labels[value]}</option>`).join("")}</select></label>` : ""}</article>`).join("") : "<p>تعهدی ثبت نشده است.</p>";
  document.querySelector("#reviews").innerHTML = reviews.length ? reviews.map((item) => `<article class="decision-row"><strong>تصمیم ${Number(item.decision_id).toLocaleString("fa-IR")}</strong><span>${escapeHtml(item.reviewer_email)} · ${escapeHtml(labels[item.status])}</span>${canWrite && item.status === "pending" && item.reviewer_email.toLowerCase() === identity.email.toLowerCase() ? `<button type="button" data-review="${Number(item.id)}" data-resolution="approved">تأیید</button> <button type="button" data-review="${Number(item.id)}" data-resolution="rejected">رد</button>` : ""}</article>`).join("") : "<p>بررسی‌ای ثبت نشده است.</p>";
  return true;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  session += 1;
  token = document.querySelector("#token").value;
  const button = form.querySelector("button");
  button.disabled = true;
  status.textContent = "در حال بارگذاری…";
  try {
    if (await loadDashboard()) {
      form.reset();
      login.hidden = true;
      dashboard.hidden = false;
      status.textContent = "";
    }
  } catch (error) {
    token = "";
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

async function updateItem(control, path, body) {
  const currentSession = session;
  control.disabled = true;
  actionStatus.textContent = "در حال ذخیره…";
  try {
    await api(path, { method: "PUT", body: JSON.stringify(body) });
    if (currentSession !== session) return;
    await loadDashboard();
    actionStatus.textContent = "تغییرات ذخیره شد.";
  } catch (error) {
    if (currentSession === session) actionStatus.textContent = error.message;
  } finally {
    control.disabled = false;
  }
}

document.querySelector("#obligations").addEventListener("change", (event) => {
  const control = event.target.closest("[data-obligation]");
  if (control) updateItem(control, `/obligations/${control.dataset.obligation}/status`, { status: control.value });
});
document.querySelector("#reviews").addEventListener("click", (event) => {
  const control = event.target.closest("[data-review]");
  if (control) updateItem(control, `/reviews/${control.dataset.review}`, { status: control.dataset.resolution });
});
document.querySelector("#audit-export").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  const currentSession = session;
  button.disabled = true;
  try {
    const data = await api("/audit-export");
    if (currentSession !== session) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "mizan-audit.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    if (currentSession === session) actionStatus.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
document.querySelector("#logout").addEventListener("click", () => {
  session += 1;
  token = "";
  form.reset();
  for (const id of ["recent-decisions", "risk-distribution", "reviews", "obligations"]) document.getElementById(id).replaceChildren();
  actionStatus.textContent = "";
  dashboard.hidden = true;
  login.hidden = false;
});
