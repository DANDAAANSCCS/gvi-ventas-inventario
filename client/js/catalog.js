// =============================================
// js/catalog.js - Catalogo de productos (Home)
// =============================================
// Consume GET /products desde la API REST del backend FastAPI.

const PAGE_SIZE = 12;
let allProducts = [];
let currentPage = 1;
let selectedProduct = null;

document.addEventListener("DOMContentLoaded", async () => {
  await loadProducts();
  setupFilters();
  document.getElementById("cart-toggle").addEventListener("click", toggleCart);
});

async function loadProducts() {
  showSpinner("products-container");
  try {
    const data = await window.api.listProducts({ only_active: true, only_in_stock: true });
    allProducts = (data || []).map(p => ({ ...p, price: Number(p.price) }));
    allProducts.sort((a, b) => a.name.localeCompare(b.name));
    populateCategories(allProducts);
    renderProducts();
  } catch (err) {
    document.getElementById("products-container").innerHTML =
      `<div class="alert alert-danger">Error al cargar productos: ${escapeHtml(err.message)}</div>`;
  }
}

function populateCategories(products) {
  const sel = document.getElementById("category-filter");
  const cats = [...new Set(products.map(p => p.category).filter(Boolean))].sort();
  cats.forEach(cat => {
    const opt = document.createElement("option");
    opt.value = cat;
    opt.textContent = cat;
    sel.appendChild(opt);
  });
}

function setupFilters() {
  document.getElementById("search-input")
    .addEventListener("input", () => { currentPage = 1; renderProducts(); });
  document.getElementById("category-filter")
    .addEventListener("change", () => { currentPage = 1; renderProducts(); });
  document.getElementById("sort-filter")
    .addEventListener("change", () => { currentPage = 1; renderProducts(); });
}

function getFilteredProducts() {
  const term = document.getElementById("search-input").value.toLowerCase().trim();
  const cat = document.getElementById("category-filter").value;
  const sort = document.getElementById("sort-filter").value;

  let result = allProducts.filter(p =>
    (!term || p.name.toLowerCase().includes(term) ||
      (p.description || "").toLowerCase().includes(term)) &&
    (!cat || p.category === cat)
  );

  if (sort === "price_asc") result.sort((a, b) => a.price - b.price);
  if (sort === "price_desc") result.sort((a, b) => b.price - a.price);
  if (sort === "name") result.sort((a, b) => a.name.localeCompare(b.name));

  return result;
}

function renderProducts() {
  const filtered = getFilteredProducts();
  const total = filtered.length;
  const pages = Math.ceil(total / PAGE_SIZE);
  const start = (currentPage - 1) * PAGE_SIZE;
  const paginated = filtered.slice(start, start + PAGE_SIZE);

  const container = document.getElementById("products-container");

  if (paginated.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🔍</div>
        <h3>Sin resultados</h3>
        <p>Intenta cambiar los filtros de busqueda</p>
      </div>`;
    document.getElementById("pagination").innerHTML = "";
    return;
  }

  container.innerHTML = `<div class="products-grid">
    ${paginated.map(p => productCardHTML(p)).join("")}
  </div>`;

  container.querySelectorAll(".product-card").forEach(card => {
    card.addEventListener("click", () => {
      const prod = allProducts.find(p => String(p.id) === card.dataset.id);
      if (prod) openProductModal(prod);
    });
  });

  renderPagination(pages);
}

function productCardHTML(p) {
  const img = p.image_url
    ? `<img src="${escapeHtml(p.image_url)}" alt="${escapeHtml(p.name)}" loading="lazy"
           onerror="this.outerHTML='<div class=&quot;product-img-placeholder&quot;>📦</div>'" />`
    : `<div class="product-img-placeholder">📦</div>`;

  return `
    <div class="product-card" data-id="${p.id}" role="button" tabindex="0">
      ${img}
      <div class="product-info">
        <div class="product-cat">${escapeHtml(p.category || "General")}</div>
        <div class="product-name">${escapeHtml(p.name)}</div>
        <div class="product-price">${formatCurrency(p.price)}</div>
        <div class="product-stock">Stock: ${p.stock}</div>
      </div>
    </div>`;
}

function renderPagination(totalPages) {
  const pag = document.getElementById("pagination");
  if (totalPages <= 1) { pag.innerHTML = ""; return; }

  let html = "";
  for (let i = 1; i <= totalPages; i++) {
    html += `<button class="page-btn ${i === currentPage ? "active" : ""}"
      onclick="goToPage(${i})">${i}</button>`;
  }
  pag.innerHTML = html;
}

function goToPage(page) {
  currentPage = page;
  renderProducts();
  document.getElementById("catalog").scrollIntoView({ behavior: "smooth" });
}

function openProductModal(product) {
  selectedProduct = product;
  document.getElementById("modal-title").textContent = product.name;
  document.getElementById("modal-body").innerHTML = `
    ${product.image_url
      ? `<img src="${escapeHtml(product.image_url)}" alt="${escapeHtml(product.name)}"
              style="width:100%;height:200px;object-fit:cover;border-radius:4px;margin-bottom:1rem"
              onerror="this.outerHTML='<div style=&quot;font-size:4rem;text-align:center;padding:1rem&quot;>📦</div>'"/>`
      : `<div style="font-size:4rem;text-align:center;padding:1rem">📦</div>`}
    <p><strong>Categoria:</strong> ${escapeHtml(product.category || "General")}</p>
    <p style="margin:8px 0"><strong>Precio:</strong>
        <span style="color:var(--primary);font-size:1.3rem;font-weight:700">
          ${formatCurrency(product.price)}
        </span>
    </p>
    <p><strong>Stock disponible:</strong> ${product.stock} unidades</p>
    ${product.description
      ? `<p style="margin-top:10px;color:var(--text-light)">${escapeHtml(product.description)}</p>`
      : ""}
    <div style="display:flex;align-items:center;gap:10px;margin-top:16px">
      <label style="font-weight:600">Cantidad:</label>
      <input type="number" id="modal-qty" value="1" min="1"
             max="${product.stock}"
             class="form-control" style="width:80px" />
    </div>`;

  document.getElementById("modal-add-btn").onclick = () => {
    const qty = parseInt(document.getElementById("modal-qty").value) || 1;
    if (qty < 1) {
      showToast("Cantidad invalida", "warning"); return;
    }
    if (addToCart(product, qty)) {
      document.getElementById("product-modal").style.display = "none";
      renderCartPanel();
    }
  };

  document.getElementById("product-modal").style.display = "flex";
}

function closeModal(event) {
  if (event.target === document.getElementById("product-modal")) {
    document.getElementById("product-modal").style.display = "none";
  }
}

function toggleCart() {
  const panel = document.getElementById("cart-panel");
  const overlay = document.getElementById("overlay");
  const isOpen = panel.classList.contains("open");
  panel.classList.toggle("open", !isOpen);
  overlay.classList.toggle("show", !isOpen);
  if (!isOpen) renderCartPanel();
}

function renderCartPanel() {
  const cart = getCart();
  const listEl = document.getElementById("cart-items-list");
  const totalEl = document.getElementById("cart-total");

  if (cart.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🛒</div>
        <h3>Tu carrito esta vacio</h3>
        <p>Agrega productos desde el catalogo</p>
      </div>`;
    totalEl.textContent = formatCurrency(0);
    return;
  }

  listEl.innerHTML = cart.map(item => `
    <div class="cart-item">
      <div class="cart-item-img" style="background:var(--bg);display:flex;
           align-items:center;justify-content:center;font-size:1.5rem">
        ${item.image_url
      ? `<img src="${escapeHtml(item.image_url)}" style="width:56px;height:56px;object-fit:cover"
             onerror="this.outerHTML='📦'" />`
      : "📦"}
      </div>
      <div class="cart-item-info">
        <div class="cart-item-name">${escapeHtml(item.name)}</div>
        <div class="cart-item-price">${formatCurrency(item.price)}</div>
        <div class="cart-item-qty">
          <button class="qty-btn" onclick="changeQty('${item.id}',-1)">−</button>
          <span>${item.qty}</span>
          <button class="qty-btn" onclick="changeQty('${item.id}',1)">+</button>
          <button class="qty-btn" style="margin-left:auto;color:var(--danger)"
            onclick="removeItem('${item.id}')">🗑</button>
        </div>
      </div>
    </div>`).join("");

  totalEl.textContent = formatCurrency(getCartTotal());
}

function changeQty(productId, delta) {
  if (delta > 0) {
    const item = getCart().find(i => String(i.id) === String(productId));
    if (item) addToCart(item, 1);
  } else {
    decreaseQty(productId);
  }
  renderCartPanel();
}

function removeItem(productId) {
  removeFromCart(productId);
  renderCartPanel();
}

function goToCheckout() {
  if (!window.apiAuth.getToken()) {
    showToast("Inicia sesion para continuar", "warning");
    setTimeout(() => window.location.href = "login.html?next=orders.html", 1500);
    return;
  }
  if (getCart().length === 0) {
    showToast("Tu carrito esta vacio", "warning");
    return;
  }
  window.location.href = "orders.html";
}
