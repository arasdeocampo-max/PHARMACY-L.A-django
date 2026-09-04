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
  function makeElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function setStyles(element, styles) {
    element.style.cssText = styles;
    return element;
  }
  function appendRow(parent, label, value, valueStyles) {
    const row = setStyles(makeElement("div"), "display:flex;justify-content:space-between");
    row.append(makeElement("span", "", label), setStyles(makeElement("span", "", value), valueStyles || ""));
    parent.appendChild(row);
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
    grid.replaceChildren();
    if (filtered.length === 0) {
      grid.appendChild(
        setStyles(
          makeElement("div", "", "No products match your search."),
          "grid-column:1/-1;text-align:center;padding:2rem;color:var(--pharma-muted);font-size:0.88rem",
        ),
      );
      return;
    }
    filtered.forEach((p) => {
        const inCart = cart.find((i) => i.id === p.id);
        const tile = makeElement("div", "pos-tile");
        tile.addEventListener("click", () => addToCart(p.id));
        if (inCart) tile.appendChild(setStyles(makeElement("div", "", inCart.qty), "position:absolute;top:6px;right:6px;width:20px;height:20px;background:var(--pharma-primary);color:#fff;border-radius:50%;font-size:0.7rem;font-weight:800;display:grid;place-items:center;z-index:1"));
        const imageWrap = makeElement("div", "pos-tile-image-wrap");
        const image = makeElement("img", "pos-tile-image");
        image.alt = p.name;
        if (p.image_url) image.src = p.image_url;
        image.addEventListener("error", () => { image.style.display = "none"; });
        imageWrap.appendChild(image);
        tile.appendChild(imageWrap);
        const details = makeElement("div");
        details.appendChild(setStyles(makeElement("div", "", p.name), "font-weight:700;font-size:0.85rem;line-height:1.2;margin-bottom:0.25rem"));
        details.appendChild(setStyles(makeElement("div", "", p.kind), "font-size:0.73rem;color:#6b7b8b;margin-bottom:0.3rem"));
        const meta = setStyles(makeElement("div"), "display:flex;align-items:center;gap:0.3rem;margin-bottom:0.3rem");
        meta.appendChild(makeElement("span", "pill-" + String(p.type).toLowerCase(), p.type));
        meta.appendChild(setStyles(makeElement("span", "", p.stock + " left"), "background:#dff4e7;color:#157a6e;border-radius:999px;padding:0.15rem 0.4rem;font-size:0.68rem;font-weight:700"));
        details.appendChild(meta);
        const footer = setStyles(makeElement("div"), "display:flex;justify-content:space-between;align-items:center");
        footer.appendChild(setStyles(makeElement("span", "", "PHP " + p.price.toFixed(2)), "font-weight:800;font-size:0.95rem"));
        const addButton = makeElement("button", "pos-add-btn", "+ Add");
        addButton.addEventListener("click", (event) => { event.stopPropagation(); addToCart(p.id); });
        footer.appendChild(addButton);
        details.appendChild(footer);
        tile.appendChild(details);
        grid.appendChild(tile);
      });
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
    area.replaceChildren();
    if (cart.length === 0) area.appendChild(setStyles(makeElement("div", "", "Cart is empty. Tap a product to add."), "text-align:center;padding:2rem 0.5rem;color:var(--pharma-muted);font-size:0.85rem"));
    cart.forEach((item) => {
      const row = setStyles(makeElement("div"), "display:flex;gap:0.65rem;padding:0.6rem 0.35rem;border-bottom:1px solid rgba(226,230,227,0.6);align-items:flex-start");
      const details = setStyles(makeElement("div"), "flex:1;min-width:0");
      details.appendChild(setStyles(makeElement("div", "", item.name), "font-weight:700;font-size:0.85rem"));
      details.appendChild(setStyles(makeElement("div", "", fmt(item.price) + " ea."), "font-size:0.74rem;color:var(--pharma-muted)"));
      const controls = setStyles(makeElement("div"), "display:flex;align-items:center;gap:0.35rem;margin-top:0.35rem");
      [["−", -1], ["+", 1]].forEach(([label, delta]) => {
        const button = setStyles(makeElement("button", "", label), "width:24px;height:24px;border:1px solid var(--pharma-border);border-radius:50%;background:#fff;cursor:pointer;font-weight:700;display:grid;place-items:center;font-size:0.9rem");
        button.addEventListener("click", () => updateQty(item.id, delta));
        if (delta === 1) controls.appendChild(makeElement("span", "", item.qty));
        controls.appendChild(button);
      });
      controls.insertBefore(controls.lastChild.previousSibling, controls.lastChild);
      details.appendChild(controls);
      row.appendChild(details);
      const summary = setStyles(makeElement("div"), "text-align:right;flex-shrink:0");
      summary.appendChild(setStyles(makeElement("div", "", fmt(item.price * item.qty)), "font-weight:800;font-size:0.9rem"));
      const remove = setStyles(makeElement("button", "", "Remove"), "background:none;border:none;color:#dc2626;cursor:pointer;font-size:0.72rem;font-weight:600;margin-top:0.3rem;font-family:inherit");
      remove.addEventListener("click", () => removeFromCart(item.id));
      summary.appendChild(remove);
      row.appendChild(summary);
      area.appendChild(row);
    });
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
    const body = $("receipt-body");
    body.replaceChildren();
    const heading = setStyles(makeElement("div"), "font-size:0.76rem;color:#6b7b8b;display:grid;gap:0.25rem;margin-bottom:0.85rem");
    appendRow(heading, "Transaction", data.transaction_id, "font-weight:700;color:#1f3b53");
    appendRow(heading, "Date", data.date);
    appendRow(heading, "Time", data.time);
    body.appendChild(heading);
    body.appendChild(setStyles(makeElement("div"), "border-top:1px dashed #cdd8e3;margin:0.85rem 0"));
    const items = setStyles(makeElement("div"), "display:grid;gap:0.5rem;margin-bottom:0.85rem");
    data.items.forEach((item) => {
      const row = makeElement("div");
      row.appendChild(setStyles(makeElement("div", "", item.name), "font-weight:700;font-size:0.85rem;color:#1a2b3d;margin-bottom:0.1rem"));
      const detail = setStyles(makeElement("div"), "display:flex;justify-content:space-between;font-size:0.8rem");
      detail.append(makeElement("span", "", `${item.qty} × ${fmt(item.price)}`), setStyles(makeElement("span", "", fmt(item.qty * parseFloat(item.price))), "font-weight:700"));
      row.appendChild(detail);
      items.appendChild(row);
    });
    body.appendChild(items);
    body.appendChild(setStyles(makeElement("div"), "border-top:1px dashed #cdd8e3;margin:0.85rem 0"));
    const totals = setStyles(makeElement("div"), "display:grid;gap:0.3rem;margin-bottom:0.85rem;font-size:0.82rem");
    appendRow(totals, "Subtotal", fmt(data.subtotal), "");
    if (data.discount > 0) appendRow(totals, "Discount", "− " + fmt(data.discount), "color:#dc2626");
    appendRow(totals, "TOTAL", fmt(data.total), "font-weight:800;font-size:1.05rem;color:var(--pharma-primary)");
    totals.lastChild.style.borderTop = "2px solid var(--pharma-primary)";
    totals.lastChild.style.paddingTop = "0.35rem";
    totals.lastChild.style.marginTop = "0.2rem";
    body.appendChild(totals);
    const payment = setStyles(makeElement("div"), "background:#f4faf9;border:1px solid #c8e6e3;border-radius:0.85rem;padding:0.85rem 1rem;margin-bottom:1.1rem;font-size:0.82rem;display:grid;gap:0.3rem");
    appendRow(payment, "Method", data.method === "gcash" ? "GCASH" : "CASH", "font-weight:700");
    if (data.method === "gcash") appendRow(payment, "Reference Number", data.payment_reference, "font-weight:700");
    else {
      appendRow(payment, "Cash Tendered", fmt(data.cash_given), "font-weight:700");
      appendRow(payment, "Change", fmt(data.change), "font-size:0.9rem;font-weight:800;color:#15803d");
    }
    body.appendChild(payment);
    const footer = setStyles(makeElement("div"), "text-align:center;font-size:0.73rem;color:#9ca3af;line-height:1.7");
    footer.appendChild(makeElement("div", "", "Thank you for your purchase!"));
    footer.appendChild(setStyles(makeElement("div", "", "L.A · BIR Accredited"), "margin-top:0.3rem;font-weight:700;color:#6b7b8b"));
    body.appendChild(footer);
    $("receipt-modal").style.display = "flex";
  }
  function closeReceipt() {
    $("receipt-modal").style.display = "none";
  }
  document.querySelector(".js-print-receipt")?.addEventListener("click", () => window.print());
  window.POS = { addToCart, removeFromCart, updateQty, clearCart };
  window.closeReceipt = closeReceipt;
  renderProducts();
  renderCart();
})();
