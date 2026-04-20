// =============================================
// js/cart.js — Lógica del carrito (localStorage)
// =============================================

const CART_KEY = "gv_cart";

/** Obtiene el carrito desde localStorage */
function getCart() {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY)) || [];
  } catch {
    return [];
  }
}

/** Guarda el carrito en localStorage y actualiza el badge */
function saveCart(cart) {
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
  updateCartBadge();
}

/** Agrega un producto al carrito o incrementa su cantidad */
function addToCart(product, qty = 1) {
  const cart = getCart();
  const existing = cart.find(i => i.id === product.id);
  if (existing) {
    // Verificar límite de stock
    if (existing.qty + qty > product.stock) {
      showToast(`Stock máximo: ${product.stock}`, "warning");
      return false;
    }
    existing.qty += qty;
  } else {
    if (qty > product.stock) {
      showToast(`Stock insuficiente`, "warning");
      return false;
    }
    cart.push({ ...product, qty });
  }
  saveCart(cart);
  showToast(`${product.name} agregado al carrito ✔`, "success");
  return true;
}

/** Quita una unidad de un producto del carrito */
function decreaseQty(productId) {
  let cart = getCart();
  const item = cart.find(i => i.id === productId);
  if (!item) return;
  if (item.qty <= 1) {
    removeFromCart(productId);
  } else {
    item.qty -= 1;
    saveCart(cart);
  }
}

/** Elimina un producto del carrito */
function removeFromCart(productId) {
  const cart = getCart().filter(i => i.id !== productId);
  saveCart(cart);
}

/** Vacía el carrito */
function clearCart() {
  saveCart([]);
}

/** Calcula el total del carrito */
function getCartTotal() {
  return getCart().reduce((sum, i) => sum + i.price * i.qty, 0);
}

/** Actualiza el badge de cantidad en el navbar */
function updateCartBadge() {
  const badge = document.getElementById("cart-badge");
  if (!badge) return;
  const count = getCart().reduce((s, i) => s + i.qty, 0);
  badge.textContent = count;
  badge.style.display = count > 0 ? "inline" : "none";
}

// Inicializar badge al cargar
document.addEventListener("DOMContentLoaded", updateCartBadge);
