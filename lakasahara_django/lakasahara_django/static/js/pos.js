/* Lakasahara Medical Supplies Co. — Sales POS */
(function () {
  "use strict";
  const shell = document.getElementById("sales-pos-shell");
  const CHECKOUT_URL = shell?.dataset.checkoutUrl || "/sales/checkout/";
  const CSRF_TOKEN = shell?.dataset.csrfToken || "";
  const PRODUCTS = JSON.parse(
    document.getElementById("products-data").textContent,
  );
  let cart = [],
    category = "All",
    query = "";
  const $ = (id) => document.getElementById(id);
  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[character]);
  }
  function fmt(n) {
    return "PHP " + parseFloat(n).toFixed(2);
  }
  function renderProducts() {
    const grid = $("product-grid");
    const filtered = PRODUCTS.filter((p) => {
      const catOk = category === "All" || p.category === category;
      const q = query.toLowerCase();
      const searchOk =
        !q ||
        p.name.toLowerCase().includes(q) ||
        p.barcode.toLowerCase().includes(q);
      return catOk && searchOk;
    });
    $("item-count").textContent =
      filtered.length + " item" + (filtered.length !== 1 ? "s" : "");
    if (filtered.length === 0) {
      grid.innerHTML =
        '<div style="grid-column:1/-1;text-align:center;padding:2rem;color:var(--pharma-muted);font-size:0.88rem">No products match your search.</div>';
      return;
    }
    grid.innerHTML = filtered
      .map((p) => {
        const inCart = cart.find((i) => i.id === p.id);
        const badge = inCart
          ? `<div style="position:absolute;top:6px;right:6px;width:20px;height:20px;background:var(--pharma-primary);color:#fff;border-radius:50%;font-size:0.7rem;font-weight:800;display:grid;place-items:center;z-index:1">${inCart.qty}</div>`
          : "";
        return `<div class="pos-tile" onclick="POS.addToCart(${p.id})">${badge}<div class="pos-tile-image-wrap"><img class="pos-tile-image" src="${escapeHtml(p.image_url || "")}" alt="${escapeHtml(p.name)}" onerror="this.style.display='none'"></div><div><div style="font-weight:700;font-size:0.85rem;line-height:1.2;margin-bottom:0.25rem">${escapeHtml(p.name)}</div><div style="font-size:0.73rem;color:#6b7b8b;margin-bottom:0.3rem">${escapeHtml(p.kind)}</div><div style="display:flex;align-items:center;gap:0.3rem;margin-bottom:0.3rem"><span class="pill-${escapeHtml(p.type.toLowerCase())}">${escapeHtml(p.type)}</span><span style="background:#dff4e7;color:#157a6e;border-radius:999px;padding:0.15rem 0.4rem;font-size:0.68rem;font-weight:700">${p.stock} left</span></div><div style="display:flex;justify-content:space-between;align-items:center"><span style="font-weight:800;font-size:0.95rem">PHP ${p.price.toFixed(2)}</span><button class="pos-add-btn" onclick="event.stopPropagation();POS.addToCart(${p.id})">+ Add</button></div></div></div>`;
      })
      .join("");
  }
  function addToCart(id) {
    const p = PRODUCTS.find((p) => p.id === id);
    if (!p || p.stock <= 0) return;
    const ex = cart.find((i) => i.id === id);
    if (ex) ex.qty = Math.min(ex.qty + 1, p.stock);
    else
      cart.push({
        id: p.id,
        name: p.name,
        price: p.price,
        qty: 1,
        stock: p.stock,
      });
    renderCart();
    renderProducts();
  }
  function removeFromCart(id) {
    cart = cart.filter((i) => i.id !== id);
    renderCart();
    renderProducts();
  }
  function updateQty(id, delta) {
    const item = cart.find((i) => i.id === id);
    if (!item) return;
    item.qty = Math.max(1, Math.min(item.qty + delta, item.stock));
    renderCart();
    renderProducts();
  }
  function clearCart() {
    cart = [];
    renderCart();
    renderProducts();
  }
  function renderCart() {
    const area = $("cart-items");
    $("cart-count").textContent =
      cart.length + " item" + (cart.length !== 1 ? "s" : "");
    if (cart.length === 0) {
      area.innerHTML =
        '<div style="text-align:center;padding:2rem 0.5rem;color:var(--pharma-muted);font-size:0.85rem">Cart is empty. Tap a product to add.</div>';
    } else {
      area.innerHTML = cart
        .map(
          (item) =>
            `<div style="display:flex;gap:0.65rem;padding:0.6rem 0.35rem;border-bottom:1px solid rgba(226,230,227,0.6);align-items:flex-start"><div style="flex:1;min-width:0"><div style="font-weight:700;font-size:0.85rem">${escapeHtml(item.name)}</div><div style="font-size:0.74rem;color:var(--pharma-muted)">PHP ${item.price.toFixed(2)} ea.</div><div style="display:flex;align-items:center;gap:0.35rem;margin-top:0.35rem"><button onclick="POS.updateQty(${item.id},-1)" style="width:24px;height:24px;border:1px solid var(--pharma-border);border-radius:50%;background:#fff;cursor:pointer;font-weight:700;display:grid;place-items:center;font-size:0.9rem">−</button><span style="min-width:28px;text-align:center;font-weight:700;font-size:0.88rem">${item.qty}</span><button onclick="POS.updateQty(${item.id},1)" style="width:24px;height:24px;border:1px solid var(--pharma-border);border-radius:50%;background:#fff;cursor:pointer;font-weight:700;display:grid;place-items:center;font-size:0.9rem">+</button></div></div><div style="text-align:right;flex-shrink:0"><div style="font-weight:800;font-size:0.9rem">${fmt(item.price * item.qty)}</div><button onclick="POS.removeFromCart(${item.id})" style="background:none;border:none;color:#dc2626;cursor:pointer;font-size:0.72rem;font-weight:600;margin-top:0.3rem;font-family:inherit">Remove</button></div></div>`,
        )
        .join("");
    }
    updateTotals();
  }
  function updateTotals() {
    const subtotal = cart.reduce((s, i) => s + i.price * i.qty, 0);
    const discount = parseFloat($("discount-input").value) || 0;
    const total = Math.max(0, subtotal - discount);
    const cash = parseFloat($("cash-input").value) || 0;
    const change = Math.max(0, cash - total);
    $("subtotal-val").textContent = fmt(subtotal);
    $("total-val").textContent = fmt(total);
    $("change-row").style.display = cash > 0 ? "flex" : "none";
    $("change-val").textContent = fmt(change);
    const btn = $("checkout-btn");
    btn.disabled = cart.length === 0;
    btn.textContent = "Complete Sale — " + fmt(total);
    btn.style.background =
      cart.length === 0 ? "#e2e6e3" : "linear-gradient(180deg,#1aa9a1,#178b85)";
    btn.style.color = cart.length === 0 ? "var(--pharma-muted)" : "#fff";
    btn.style.cursor = cart.length === 0 ? "not-allowed" : "pointer";
  }
  function updatePaymentMethod() {
    const isGcash = $("payment-method").value === "gcash";
    $("gcash-reference-wrap").classList.toggle("hidden", !isGcash);
    $("gcash-reference").required = isGcash;
    $("cash-input").disabled = isGcash;
    if (isGcash) $("cash-input").value = "";
    updateTotals();
  }
  document.querySelectorAll(".pos-cat-btn").forEach((btn) =>
    btn.addEventListener("click", () => {
      category = btn.dataset.cat;
      document
        .querySelectorAll(".pos-cat-btn")
        .forEach((b) =>
          b.classList.toggle("active", b.dataset.cat === category),
        );
      renderProducts();
    }),
  );
  $("search-input").addEventListener("input", (e) => {
    query = e.target.value;
    renderProducts();
  });
  $("discount-input").addEventListener("input", updateTotals);
  $("cash-input").addEventListener("input", updateTotals);
  $("gcash-reference").addEventListener("input", (event) => {
    event.target.value = event.target.value.replace(/\D/g, "");
  });
  $("payment-method").addEventListener("change", updatePaymentMethod);
  $("checkout-btn").addEventListener("click", async () => {
    if (cart.length === 0) return;
    const discount = parseFloat($("discount-input").value) || 0;
    const cash_given = parseFloat($("cash-input").value) || 0;
    const method = $("payment-method").value;
    const payment_reference = $("gcash-reference").value.trim();
    const idempotency_key = crypto.randomUUID();
    if (method === "gcash" && !payment_reference) {
      $("gcash-reference").focus();
      alert("Please enter the GCash reference number.");
      return;
    }
    try {
      const resp = await fetch(CHECKOUT_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": CSRF_TOKEN,
        },
        body: JSON.stringify({
          cart: cart.map((item) => ({ id: item.id, qty: item.qty })),
          discount,
          cash_given,
          method,
          payment_reference,
          idempotency_key,
        }),
      });
      const data = await resp.json();
      if (data.success) {
        showReceipt(data);
        cart = [];
        $("discount-input").value = "";
        $("cash-input").value = "";
        $("gcash-reference").value = "";
        $("payment-method").value = "cash";
        updatePaymentMethod();
        renderCart();
        renderProducts();
      } else alert("Checkout failed: " + (data.error || "Unknown error"));
    } catch (e) {
      alert("Network error: " + e.message);
    }
  });
  function showReceipt(data) {
    const items = data.items
      .map(
        (i) =>
          `<div><div style="font-weight:700;font-size:0.85rem;color:#1a2b3d;margin-bottom:0.1rem">${escapeHtml(i.name)}</div><div style="display:flex;justify-content:space-between;font-size:0.8rem"><span style="color:#6b7b8b">${i.qty} × PHP ${parseFloat(i.price).toFixed(2)}</span><span style="font-weight:700">PHP ${(i.qty * parseFloat(i.price)).toFixed(2)}</span></div></div>`,
      )
      .join("");
    $("receipt-body").innerHTML =
      `<div style="font-size:0.76rem;color:#6b7b8b;display:grid;gap:0.25rem;margin-bottom:0.85rem"><div style="display:flex;justify-content:space-between"><span>Transaction</span><span style="font-weight:700;color:#1f3b53">${data.transaction_id}</span></div><div style="display:flex;justify-content:space-between"><span>Date</span><span>${data.date}</span></div><div style="display:flex;justify-content:space-between"><span>Time</span><span>${data.time}</span></div></div><div style="border-top:1px dashed #cdd8e3;margin:0.85rem 0"></div><div style="display:grid;gap:0.5rem;margin-bottom:0.85rem">${items}</div><div style="border-top:1px dashed #cdd8e3;margin:0.85rem 0"></div><div style="display:grid;gap:0.3rem;margin-bottom:0.85rem;font-size:0.82rem"><div style="display:flex;justify-content:space-between;color:#6b7b8b"><span>Subtotal</span><span>PHP ${parseFloat(data.subtotal).toFixed(2)}</span></div>${data.discount > 0 ? `<div style="display:flex;justify-content:space-between;color:#dc2626"><span>Discount</span><span>− PHP ${parseFloat(data.discount).toFixed(2)}</span></div>` : ""}<div style="display:flex;justify-content:space-between;font-weight:800;font-size:1.05rem;color:var(--pharma-primary);border-top:2px solid var(--pharma-primary);padding-top:0.35rem;margin-top:0.2rem"><span>TOTAL</span><span>PHP ${parseFloat(data.total).toFixed(2)}</span></div></div><div style="background:#f4faf9;border:1px solid #c8e6e3;border-radius:0.85rem;padding:0.85rem 1rem;margin-bottom:1.1rem;font-size:0.82rem;display:grid;gap:0.3rem"><div style="display:flex;justify-content:space-between"><span style="color:#6b7b8b">Method</span><span style="font-weight:700">CASH</span></div><div style="display:flex;justify-content:space-between"><span style="color:#6b7b8b">Cash Tendered</span><span style="font-weight:700">PHP ${parseFloat(data.cash_given).toFixed(2)}</span></div><div style="display:flex;justify-content:space-between;font-size:0.9rem;font-weight:800;color:#15803d"><span>Change</span><span>PHP ${parseFloat(data.change).toFixed(2)}</span></div></div><div style="text-align:center;font-size:0.73rem;color:#9ca3af;line-height:1.7"><div>Thank you for your purchase!</div><div style="margin-top:0.3rem;font-weight:700;color:#6b7b8b">L.A · BIR Accredited</div></div>`;
    const paymentSummary = $("receipt-body").lastElementChild;
    if (paymentSummary && data.method === "gcash") {
      paymentSummary.innerHTML = paymentSummary.innerHTML
        .replace("CASH", "GCASH")
        .replace(
          /<div style="display:flex;justify-content:space-between"><span style="color:#6b7b8b">Cash Tendered<\/span>[\s\S]*?<\/div><div style="display:flex;justify-content:space-between;font-size:0.9rem;font-weight:800;color:#15803d"><span>Change<\/span>[\s\S]*?<\/div>/,
          `<div style="display:flex;justify-content:space-between"><span style="color:#6b7b8b">Reference Number</span><span style="font-weight:700">${data.payment_reference}</span></div>`,
        );
    }
    $("receipt-modal").style.display = "flex";
  }
  function closeReceipt() {
    $("receipt-modal").style.display = "none";
  }
  window.POS = { addToCart, removeFromCart, updateQty, clearCart };
  window.closeReceipt = closeReceipt;
  renderProducts();
  renderCart();
})();
