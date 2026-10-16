const state = {
  products: [],
  categories: [],
  cart: null,
  token: localStorage.getItem("trendaura_token"),
  accountMode: "login",
};

const $ = (selector) => document.querySelector(selector);
const productGrid = $("#product-grid");
const emptyState = $("#empty-state");
const toast = $("#toast");

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(`/api/v1${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Something went wrong.");
  return data;
}

function money(value) {
  return `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2600);
}

function renderProducts(products = state.products) {
  productGrid.innerHTML = products.map((product, index) => `
    <article class="product-card" style="animation-delay: ${index * 70}ms">
      <div class="product-image">
        ${product.image_url ? `<img src="${product.image_url}" alt="${product.name}" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('div'), { className: 'image-fallback', textContent: 'TA' }))" />` : '<div class="image-fallback">TA</div>'}
      </div>
      <div class="product-meta">
        <div><p class="product-name">${product.name}</p><p class="product-category">${product.category?.name || "Collection"}</p></div>
        <span class="product-price">${money(product.price)}</span>
      </div>
      <button class="add-button" type="button" data-product-id="${product.id}">Add to bag <span aria-hidden="true">&#8594;</span></button>
    </article>
  `).join("");
  emptyState.classList.toggle("hidden", products.length > 0);
}

function renderCategories() {
  const tabs = $("#category-tabs");
  tabs.innerHTML = '<button class="tab active" type="button" data-category="">All pieces</button>' + state.categories.map((category) => `<button class="tab" type="button" data-category="${category.slug}">${category.name}</button>`).join("");
}

async function loadProducts(params = {}) {
  const search = new URLSearchParams(params).toString();
  try {
    state.products = await api(`/products${search ? `?${search}` : ""}`);
    renderProducts();
  } catch (error) {
    productGrid.innerHTML = `<p class="empty-state">${error.message}</p>`;
  }
}

function renderCart() {
  const content = $("#cart-content");
  const footer = $("#cart-footer");
  const items = state.cart?.items || [];
  $("#cart-count").textContent = items.reduce((total, item) => total + item.quantity, 0);
  if (!items.length) {
    content.innerHTML = '<p class="empty-cart">Your bag is waiting for something good.</p>';
    footer.innerHTML = "";
    return;
  }
  content.innerHTML = items.map((item) => `
    <div class="cart-item">
      <div><p class="cart-item-name">${productName(item.product_id)}</p><p class="cart-item-detail">${item.quantity} &times; ${money(item.unit_price)}</p></div>
      <div><p>${money(item.subtotal)}</p><button class="remove-item" data-item-id="${item.id}" type="button">Remove</button></div>
    </div>
  `).join("");
  footer.innerHTML = `<div class="cart-total"><span>Total</span><strong>${money(state.cart.subtotal)}</strong></div><button class="button button-dark full-width" id="checkout-button" type="button">Checkout <span aria-hidden="true">&#8599;</span></button>`;
}

function productName(productId) {
  return state.products.find((product) => product.id === productId)?.name || "Selected piece";
}

async function refreshCart() {
  if (!state.token) {
    state.cart = null;
    renderCart();
    return;
  }
  try { state.cart = await api("/cart"); } catch { state.cart = null; }
  renderCart();
}

function formatOrderStatus(status) {
  return status.replaceAll("_", " ");
}

function demoTransferFor(orderNumber) {
  const transfers = JSON.parse(localStorage.getItem("trendaura_demo_transfers") || "[]");
  return transfers.find((transfer) => transfer.reference.includes(orderNumber));
}

function renderOrders(orders = []) {
  const list = $("#orders-list");
  if (!state.token) {
    list.innerHTML = '<p class="orders-empty">Sign in to see your order history.</p>';
    return;
  }
  if (!orders.length) {
    list.innerHTML = '<p class="orders-empty">Your order history will appear here after checkout.</p>';
    return;
  }
  list.innerHTML = orders.map((order) => {
    const eligible = ["confirmed", "shipped", "delivered"].includes(order.status);
    const date = new Date(order.created_at).toLocaleDateString("en-PK", { dateStyle: "medium" });
    const demoTransfer = demoTransferFor(order.order_number);
    const actionLabel = order.status === "refunded" || order.status === "return_approved"
      ? "Refund approved"
      : order.status === "under_review" ? "Under review" : "Return order";
    return `<article class="order-row">
      <div><p class="order-number">${order.order_number}</p><p class="order-date">${date}</p></div>
      <p class="order-payment">${order.payment_method === "cod" ? "Cash on delivery" : "Bank transfer"}${demoTransfer ? `<span class="demo-payment">Demo: ${demoTransfer.status}</span>` : ""}</p>
      <div><span class="order-status">${formatOrderStatus(order.status)}</span><p class="order-date">${money(order.final_amount)}</p></div>
      <button class="return-button" type="button" data-order-id="${order.id}" ${eligible ? "" : "disabled"}>${actionLabel}</button>
    </article>`;
  }).join("");
}

async function loadOrders() {
  if (!state.token) {
    renderOrders();
    return;
  }
  try { renderOrders(await api("/orders")); } catch (error) { $("#orders-list").innerHTML = `<p class="orders-empty">${error.message}</p>`; }
}

function openPanel(panel) {
  $("#overlay").classList.remove("hidden");
  panel.classList.add("open");
  if (panel === $("#cart-drawer")) panel.setAttribute("aria-hidden", "false");
}

function closePanels() {
  $("#overlay").classList.add("hidden");
  $("#cart-drawer").classList.remove("open");
  $("#cart-drawer").setAttribute("aria-hidden", "true");
  $("#account-modal").classList.add("hidden");
  $("#checkout-modal").classList.add("hidden");
}

function openModal(modal) {
  $("#overlay").classList.remove("hidden");
  modal.classList.remove("hidden");
}

function setAccountMode(mode) {
  state.accountMode = mode;
  const registering = mode === "register";
  $("#name-field").classList.toggle("hidden", !registering);
  $("#account-submit").textContent = registering ? "Create account" : "Sign in";
  $("#account-mode").textContent = registering ? "Already have an account? Sign in" : "Need an account? Create one";
  $("#account-title").textContent = registering ? "Create your account" : "Your account";
  $("#account-copy").textContent = registering ? "A few details and you are ready to go." : "Sign in to keep your bag and check out.";
  $("#account-message").textContent = "";
}

async function handleAccount(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = Object.fromEntries(form.entries());
  try {
    let response;
    if (state.accountMode === "register") {
      await api("/auth/register", { method: "POST", body: JSON.stringify(payload) });
      response = await api("/auth/login", { method: "POST", body: JSON.stringify({ email: payload.email, password: payload.password }) });
    } else {
      response = await api("/auth/login", { method: "POST", body: JSON.stringify({ email: payload.email, password: payload.password }) });
    }
    state.token = response.access_token;
    localStorage.setItem("trendaura_token", state.token);
    closePanels();
    await refreshCart();
    await loadOrders();
    showToast("You are signed in.");
  } catch (error) {
    $("#account-message").textContent = error.message;
  }
}

async function addToCart(productId) {
  if (!state.token) {
    openModal($("#account-modal"));
    $("#account-message").textContent = "Sign in to add pieces to your bag.";
    return;
  }
  try {
    state.cart = await api("/cart/items", { method: "POST", body: JSON.stringify({ product_id: Number(productId), quantity: 1 }) });
    renderCart();
    openPanel($("#cart-drawer"));
  } catch (error) { showToast(error.message); }
}

async function handleCheckout(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target).entries());
  const shipping_address = { first_name: data.first_name, last_name: data.last_name, phone: data.phone, street_address: data.street_address, city: data.city, postal_code: data.postal_code };
  try {
    const order = await api("/orders/checkout", { method: "POST", body: JSON.stringify({ payment_method: data.payment_method, shipping_address }) });
    closePanels();
    event.target.reset();
    await refreshCart();
    showToast(`Order ${order.order_number} placed.`);
  } catch (error) { $("#checkout-message").textContent = error.message; }
}

$("#product-grid").addEventListener("click", (event) => {
  const button = event.target.closest("[data-product-id]");
  if (button) addToCart(button.dataset.productId);
});
$("#category-tabs").addEventListener("click", (event) => {
  const button = event.target.closest("[data-category]");
  if (!button) return;
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
  button.classList.add("active");
  const query = button.dataset.category ? { category: button.dataset.category } : {};
  const search = $("#search-input").value.trim();
  if (search) query.search = search;
  loadProducts(query);
});
$("#search-input").addEventListener("input", (event) => {
  const activeCategory = document.querySelector(".tab.active")?.dataset.category || "";
  const query = { ...(activeCategory ? { category: activeCategory } : {}), ...(event.target.value ? { search: event.target.value } : {}) };
  loadProducts(query);
});
$("#cart-button").addEventListener("click", () => openPanel($("#cart-drawer")));
$("#close-cart").addEventListener("click", closePanels);
$("#overlay").addEventListener("click", closePanels);
$("#account-button").addEventListener("click", () => openModal($("#account-modal")));
$("#close-account").addEventListener("click", closePanels);
$("#close-checkout").addEventListener("click", closePanels);
$("#account-form").addEventListener("submit", handleAccount);
$("#account-mode").addEventListener("click", () => setAccountMode(state.accountMode === "login" ? "register" : "login"));
$("#checkout-form").addEventListener("submit", handleCheckout);
$("#sign-out").addEventListener("click", () => { state.token = null; localStorage.removeItem("trendaura_token"); closePanels(); refreshCart(); showToast("Signed out."); });
$("#orders-list").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-order-id]:not(:disabled)");
  if (!button) return;
  if (!window.confirm("Request a return for this order?")) return;
  try {
    await api(`/orders/${button.dataset.orderId}/return`, { method: "POST" });
    await loadOrders();
    showToast("Return request submitted.");
  } catch (error) { showToast(error.message); }
});
window.addEventListener("storage", (event) => {
  if (event.key === "trendaura_demo_transfers") loadOrders();
});
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) loadOrders();
});
$("#cart-content").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-item-id]");
  if (!button) return;
  try { state.cart = await api(`/cart/items/${button.dataset.itemId}`, { method: "DELETE" }); renderCart(); } catch (error) { showToast(error.message); }
});
$("#cart-footer").addEventListener("click", (event) => {
  if (event.target.closest("#checkout-button")) {
    if (!state.token) return openModal($("#account-modal"));
    openModal($("#checkout-modal"));
  }
});

async function init() {
  try {
    state.categories = await api("/products/categories");
    renderCategories();
    await loadProducts();
    await refreshCart();
    await loadOrders();
  } catch (error) { productGrid.innerHTML = `<p class="empty-state">${error.message}</p>`; }
}

init();
