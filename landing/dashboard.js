const form = document.querySelector("#token-form");
const login = document.querySelector("#login");
const dashboard = document.querySelector("#dashboard");
const status = document.querySelector("#login-status");
let token = "";

const escapeHtml = (text) => String(text).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);

async function loadDashboard() {
  const response = await fetch("/dashboard", { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error("دسترسی به داشبورد ممکن نیست.");
  const data = await response.json();
  document.querySelector("#decision-count").textContent = data.decision_count.toLocaleString("fa-IR");
  document.querySelector("#critical-count").textContent = data.critical_decision_count.toLocaleString("fa-IR");
  document.querySelector("#alert-count").textContent = data.unread_alert_count.toLocaleString("fa-IR");
  document.querySelector("#risk-distribution").innerHTML = Object.entries(data.risk_distribution).map(([level, count]) => `<div class="risk-row"><span>${escapeHtml(level)}</span><b>${Number(count).toLocaleString("fa-IR")}</b></div>`).join("");
  document.querySelector("#recent-decisions").innerHTML = data.recent_decisions.length ? data.recent_decisions.map((decision) => `<article class="decision-row"><strong>${escapeHtml(decision.title)}</strong><span>${escapeHtml(decision.risk_level)} · ${new Date(decision.created_at).toLocaleDateString("fa-IR")}</span></article>`).join("") : "<p>هنوز تصمیمی ثبت نشده است.</p>";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault(); token = document.querySelector("#token").value;
  try { await loadDashboard(); login.hidden = true; dashboard.hidden = false; } catch (error) { status.textContent = error.message; }
});
document.querySelector("#logout").addEventListener("click", () => { token = ""; form.reset(); dashboard.hidden = true; login.hidden = false; });
