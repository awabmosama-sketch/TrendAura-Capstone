const query = new URLSearchParams(window.location.search);
const orderId = query.get("order_id");
const token = localStorage.getItem("trendaura_token");
const form = document.querySelector("#refund-request-form");
const message = document.querySelector("#refund-message");
const orderNumber = document.querySelector("#order-number");

async function loadOrder() {
  if (!token || !orderId) {
    message.textContent = "Sign in and choose an order before requesting a refund.";
    form.querySelector("button").disabled = true;
    return;
  }
  const response = await fetch(`/api/v1/orders/${orderId}`, { headers: { Authorization: `Bearer ${token}` } });
  const order = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(order.detail || "Order unavailable.");
  orderNumber.value = order.order_number;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button");
  button.disabled = true;
  message.textContent = "Sending your request to the refund agent...";
  try {
    const response = await fetch(`/api/v1/orders/${orderId}/return`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ reason: new FormData(form).get("reason") }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "Refund request failed.");
    const escalated = data.status === "under_review";
    message.textContent = escalated
      ? "The AI prepared your case for team review. We will update the order after a team member decides."
      : "The AI approved your refund request. Your order has been marked for refund.";
    form.querySelector("textarea").value = "";
  } catch (error) {
    message.textContent = error.message;
    button.disabled = false;
  }
});

loadOrder().catch((error) => { message.textContent = error.message; });
