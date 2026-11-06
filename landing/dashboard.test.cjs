const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const vm = require("node:vm");

function workspace(role = "analyst") {
  const elements = new Map();
  const element = (selector) => {
    if (!elements.has(selector)) elements.set(selector, {
      innerHTML: "", textContent: "", disabled: false, hidden: false,
      listeners: {}, addEventListener(name, fn) { this.listeners[name] = fn; },
      reset() {}, replaceChildren() { this.innerHTML = ""; },
      querySelector: (child) => element(`${selector} ${child}`),
    });
    return elements.get(selector);
  };
  const data = {
    "/me": { role, email: "reviewer@example.com" },
    "/dashboard": { decision_count: 55, critical_decision_count: 2, unread_alert_count: 1, risk_distribution: { high: 2 }, recent_decisions: [] },
    "/obligations": [{ id: 1, title: "<script>unsafe</script>", due_on: "2027-01-01", status: "open" }],
    "/reviews": [{ id: 1, decision_id: 1, reviewer_email: "reviewer@example.com", status: "pending" }, { id: 2, decision_id: 2, reviewer_email: "other@example.com", status: "pending" }],
  };
  const context = vm.createContext({
    document: { querySelector: element, getElementById: (id) => element(`#${id}`) },
    fetch: async (path) => ({ ok: true, json: async () => data[path] }),
  });
  vm.runInContext(readFileSync(join(__dirname, "dashboard.js"), "utf8"), context);
  return { context, element, data };
}

test("viewers see escaped records without mutation controls", async () => {
  const { context, element } = workspace("viewer");
  assert.equal(await vm.runInContext("loadDashboard()", context), true);
  assert.match(element("#obligations").innerHTML, /&lt;script&gt;/);
  assert.doesNotMatch(element("#obligations").innerHTML, /<select/);
  assert.doesNotMatch(element("#reviews").innerHTML, /data-review/);
});

test("analysts can update obligations and only their assigned pending review", async () => {
  const { context, element } = workspace();
  await vm.runInContext("loadDashboard()", context);
  assert.match(element("#obligations").innerHTML, /data-obligation="1"/);
  assert.match(element("#reviews").innerHTML, /data-review="1"/);
  assert.doesNotMatch(element("#reviews").innerHTML, /data-review="2"/);
});

test("logout clears sensitive records and ignores pending dashboard responses", async () => {
  const { context, element } = workspace();
  const pending = vm.runInContext("loadDashboard()", context);
  element("#logout").listeners.click();
  assert.equal(await pending, false);
  assert.equal(element("#reviews").innerHTML, "");
  assert.equal(element("#obligations").innerHTML, "");
  assert.equal(element("#dashboard").hidden, true);
});

test("permission failures produce a localized error", async () => {
  const { context } = workspace();
  context.fetch = async () => ({ ok: false, status: 403 });
  await assert.rejects(vm.runInContext('api("/dashboard")', context), /اجازهٔ انجام/);
});
