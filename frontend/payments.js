const $ = (selector) => document.querySelector(selector);
const BALANCE_KEY = "trendaura_payment_balance";
let balance = Number(localStorage.getItem(BALANCE_KEY) || 0);
let orders = [];

async function loadOrders() {
  const token = localStorage.getItem("trendaura_token");
  if (!token) {
    $("#payment-orders").innerHTML = '<p class="orders-empty">Sign in on the storefront to see your orders and request refunds.</p>';
    return;
  }
  try {
    const response = await fetch("/api/v1/orders", { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error("Orders unavailable");
    orders = await response.json();
    renderOrders();
  } catch (error) {
    $("#payment-orders").innerHTML = `<p class="orders-empty">${error.message}</p>`;
  }
}

function money(value) {
  return `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;
}

function saveBalance() {
  localStorage.setItem(BALANCE_KEY, String(balance));
}

function renderBalance() {
  $("#available-balance").textContent = money(balance);
}

function renderOrders() {
  const list = $("#payment-orders");
  if (!orders.length) {
    list.innerHTML = '<p class="orders-empty">Your order history will appear here after checkout.</p>';
    return;
  }
  list.innerHTML = orders.map((order) => {
    const canPay = ["pending_verification", "pending_on_delivery"].includes(order.payment_status) && !["cancelled", "refunded", "under_review"].includes(order.status);
    const canRefund = order.payment_status === "paid" && !["refunded", "under_review"].includes(order.status);
    const action = order.status === "refunded" ? "Refund approved" : order.status === "under_review" ? "Under review" : canRefund ? "Request refund" : "Refund available after payment";
    return `<article class="payment-order">
      <div><strong>${order.order_number}</strong><span>${new Date(order.created_at).toLocaleDateString("en-PK", { dateStyle: "medium" })}</span></div>
      <div><strong>${money(order.final_amount)}</strong><span>${order.payment_status.replaceAll("_", " ")}</span></div>
      <span class="order-status">${order.status.replaceAll("_", " ")}</span>
      ${canPay ? `<button class="pay-button" type="button" data-pay-order-id="${order.id}">Pay now</button>` : canRefund ? `<a class="refund-button" href="/refund.html?order_id=${order.id}">Request refund</a>` : `<button class="refund-button" type="button" disabled>${action}</button>`}
    </article>`
  }).join("");
}

$("#add-credit").addEventListener("click", () => {
  balance += 5000;
  saveBalance();
  renderBalance();
});

$("#payment-orders").addEventListener("click", (event) => {
  const payButton = event.target.closest("[data-pay-order-id]:not(:disabled)");
  if (payButton) {
    payOrder(payButton.dataset.payOrderId, payButton);
    return;
  }
});

async function payOrder(orderId, button) {
  const order = orders.find((item) => String(item.id) === String(orderId));
  if (!order) return;
  if (balance < Number(order.final_amount)) {
    window.alert(`Add ${money(Number(order.final_amount) - balance)} more before paying this order.`);
    return;
  }
  button.disabled = true;
  const token = localStorage.getItem("trendaura_token");
  try {
    const response = await fetch(`/api/v1/orders/${orderId}/pay`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "Payment failed.");
    balance -= Number(order.final_amount);
    saveBalance();
    renderBalance();
    await loadOrders();
  } catch (error) {
    button.disabled = false;
    window.alert(error.message);
  }
}

renderBalance();
loadOrders();
