const token = localStorage.getItem("trendaura_token");
const stats = document.querySelector("#admin-stats");
const fraudList = document.querySelector("#fraud-list");

async function api(path, options = {}) {
  const response = await fetch(`/api/v1${path}`, { ...options, headers: { Authorization: `Bearer ${token}`, ...(options.headers || {}) } });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Request failed.");
  return data;
}

function renderStats(data) {
  stats.innerHTML = Object.entries({ "Paid revenue": `PKR ${Number(data.paid_revenue).toLocaleString("en-PK")}`, Orders: data.orders, Users: data.users, "Pending refunds": data.pending_refunds, "Open fraud flags": data.open_fraud_flags }).map(([label, value]) => `<article class="admin-stat"><span>${label}</span><strong>${value}</strong></article>`).join("");
}

function renderFraud(flags) {
  fraudList.innerHTML = flags.length ? flags.map((flag) => `<div class="fraud-item"><strong>Order #${flag.order_id}</strong><span>${flag.verdict} / score ${flag.fraud_score}</span><button type="button" data-release-id="${flag.order_id}">Release</button></div>`).join("") : '<p class="orders-empty">No unresolved fraud flags.</p>';
}

function renderPricing(suggestions) {
  const list = document.querySelector("#pricing-list");
  list.innerHTML = suggestions.length ? suggestions.slice(0, 8).map((suggestion) => `<div class="pricing-item"><strong>${suggestion.product_name}</strong><span>${suggestion.action}: PKR ${Number(suggestion.current_price).toLocaleString("en-PK")} -> PKR ${Number(suggestion.suggested_price).toLocaleString("en-PK")}</span><small>${suggestion.reason}</small>${suggestion.is_applied ? "<em>Applied</em>" : `<button type="button" data-apply-price="${suggestion.id}">Apply</button>`}</div>`).join("") : '<p class="orders-empty">No audit results yet.</p>';
}

async function load() {
  try {
    const [dashboardStats, flags, suggestions] = await Promise.all([api("/admin/stats"), api("/admin/fraud/flags"), api("/admin/pricing-suggestions")]);
    renderStats(dashboardStats);
    renderFraud(flags);
    renderPricing(suggestions);
  } catch (error) {
    stats.innerHTML = `<p class="orders-empty">${error.message}</p>`;
  }
}

document.querySelector("#run-pricing").addEventListener("click", async () => {
  const message = document.querySelector("#pricing-message");
  try {
    const suggestions = await api("/admin/pricing-audit", { method: "POST" });
    message.textContent = `${suggestions.length} pricing suggestions created.`;
    renderPricing(await api("/admin/pricing-suggestions"));
  } catch (error) { message.textContent = error.message; }
});

document.querySelector("#pricing-list").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-apply-price]");
  if (!button) return;
  await api(`/admin/pricing-suggestions/${button.dataset.applyPrice}/apply`, { method: "POST" });
  load();
});

fraudList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-release-id]");
  if (!button) return;
  await api(`/admin/fraud/${button.dataset.releaseId}/release`, { method: "POST" });
  load();
});

load();
