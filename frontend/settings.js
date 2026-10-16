const profile = document.querySelector("#settings-profile");
const adminSetting = document.querySelector("#admin-setting");
const token = localStorage.getItem("trendaura_token");

async function loadSettings() {
  if (!token) {
    profile.innerHTML = '<p class="orders-empty">Sign in from the storefront to access your settings.</p>';
    return;
  }
  const response = await fetch("/api/v1/auth/me", { headers: { Authorization: `Bearer ${token}` } });
  const user = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(user.detail || "Account unavailable.");
  profile.innerHTML = `<strong>${user.full_name}</strong><span>${user.email}</span><span>Role: ${user.role}</span>`;
  if (user.role === "admin") adminSetting.classList.remove("hidden");
}

loadSettings().catch((error) => { profile.innerHTML = `<p class="orders-empty">${error.message}</p>`; });
