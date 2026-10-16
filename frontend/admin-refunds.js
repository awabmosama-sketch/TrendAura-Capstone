const queue = document.querySelector("#refund-queue");
const token = localStorage.getItem("trendaura_token");

function money(value) {
  return `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;
}

async function api(path, options = {}) {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers: { Authorization: `Bearer ${token}`, ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Request failed.");
  return data;
}

function render(refunds) {
  if (!refunds.length) {
    queue.innerHTML = '<p class="orders-empty">No refund requests are waiting for team review.</p>';
    return;
  }
  queue.innerHTML = refunds.map((refund) => `
    <article class="refund-case">
      <div class="refund-case-header"><div><p class="eyebrow">Case #${refund.id}</p><h3>${refund.order_number}</h3></div><strong>${money(refund.amount)}</strong></div>
      <div class="refund-case-grid">
        <div><span class="case-label">Customer reason</span><p>${refund.customer_reason || "No reason provided."}</p></div>
        <div><span class="case-label">AI recommendation</span><p>${refund.ai_decision === "approved" ? "Approve within the refund policy." : "Reject or review outside the refund policy."} ${refund.ai_note || ""}</p></div>
      </div>
      <div class="refund-case-meta"><span>Order: ${refund.order_status.replaceAll("_", " ")}</span><span>Payment: ${refund.payment_status.replaceAll("_", " ")}</span><span>${new Date(refund.created_at).toLocaleString("en-PK", { dateStyle: "medium", timeStyle: "short" })}</span></div>
      <div class="refund-case-actions"><button class="button button-dark" type="button" data-decision="approve" data-id="${refund.id}">Approve refund</button><button class="text-button" type="button" data-decision="reject" data-id="${refund.id}">Reject request</button></div>
    </article>
  `).join("");
}

async function loadRefunds() {
  try {
    render(await api("/admin/refunds"));
  } catch (error) {
    queue.innerHTML = `<p class="orders-empty">${error.message}</p>`;
  }
}

queue.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-decision]");
  if (!button) return;
  button.disabled = true;
  try {
    await api(`/admin/refunds/${button.dataset.id}/${button.dataset.decision}`, { method: "POST" });
    await loadRefunds();
  } catch (error) {
    window.alert(error.message);
    button.disabled = false;
  }
});

document.querySelector("#refresh-refunds").addEventListener("click", loadRefunds);
loadRefunds();
