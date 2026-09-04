/* Lakasahara Medical Supplies Co. - Sales POS */
(function () {
  "use strict";
  const shell = document.getElementById("sales-pos-shell");
  const productsElement = document.getElementById("products-data");
  if (!shell || !productsElement) return;
  const checkoutUrl = shell.dataset.checkoutUrl || "/sales/checkout/";
  const csrfToken = shell.dataset.csrfToken || "";
  const parsedProducts = JSON.parse(productsElement.textContent || "[]");
  const products = typeof parsedProducts === "string" ? JSON.parse(parsedProducts) : parsedProducts;
  let cart = [];
  let category = "All";
  let query = "";
  const get = (id) => document.getElementById(id);
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const styled = (node, styles) => { node.style.cssText = styles; return node; };
  const money = (value) => "PHP " + (Number(value) || 0).toFixed(2);
  const row = (parent, label, value, styles) => {
    const line = styled(element("div"), "display:flex;justify-content:space-between");
    line.append(element("span", "", label), styled(element("span", "", value), styles || ""));
    parent.appendChild(line);
    return line;
  };
  function renderProducts() {
    const grid = get("product-grid");
    if (!grid) return;
    const filtered = products.filter((product) => {
      const name = String(product.name || "");
      const barcode = String(product.barcode || "");
      return (category === "All" || product.category === category) && (!query || name.toLowerCase().includes(query) || barcode.toLowerCase().includes(query));
    });
    get("item-count").textContent = filtered.length + " item" + (filtered.length === 1 ? "" : "s");
    grid.replaceChildren();
    if (!filtered.length) {
      grid.appendChild(styled(element("div", "", "No products match your search."), "grid-column:1/-1;text-align:center;padding:2rem;color:var(--pharma-muted);font-size:0.88rem"));
      return;
    }
    filtered.forEach((product) => {
      const tile = element("div", "pos-tile");
      tile.addEventListener("click", () => addToCart(product.id));
      const inCart = cart.find((item) => item.id === product.id);
      if (inCart) tile.appendChild(styled(element("div", "", inCart.qty), "position:absolute;top:6px;right:6px;width:20px;height:20px;background:var(--pharma-primary);color:#fff;border-radius:50%;font-size:0.7rem;font-weight:800;display:grid;place-items:center;z-index:1"));
      const imageWrap = element("div", "pos-tile-image-wrap");
      const image = element("img", "pos-tile-image");
      image.alt = String(product.name || "Product");
      if (product.image_url) image.src = product.image_url;
      image.addEventListener("error", () => { image.style.display = "none"; });
      imageWrap.appendChild(image);
      tile.appendChild(imageWrap);
      const details = element("div");
      details.append(styled(element("div", "", product.name || "Product"), "font-weight:700;font-size:0.85rem;line-height:1.2;margin-bottom:0.25rem"));
      details.append(styled(element("div", "", product.kind || ""), "font-size:0.73rem;color:#6b7b8b;margin-bottom:0.3rem"));
      const meta = styled(element("div"), "display:flex;align-items:center;gap:0.3rem;margin-bottom:0.3rem");
      meta.append(element("span", "pill-" + String(product.type || "").toLowerCase(), product.type || ""), styled(element("span", "", String(product.stock || 0) + " left"), "background:#dff4e7;color:#157a6e;border-radius:999px;padding:0.15rem 0.4rem;font-size:0.68rem;font-weight:700"));
      details.appendChild(meta);
      const footer = styled(element("div"), "display:flex;justify-content:space-between;align-items:center");
      footer.appendChild(styled(element("span", "", money(product.price)), "font-weight:800;font-size:0.95rem"));
      const add = element("button", "pos-add-btn", "+ Add");
      add.addEventListener("click", (event) => { event.stopPropagation(); addToCart(product.id); });
      footer.appendChild(add);
      details.appendChild(footer);
      tile.appendChild(details);
      grid.appendChild(tile);
    });
  }
  function addToCart(id) {
    const product = products.find((item) => item.id === id);
    if (!product || product.stock <= 0) return;
    const existing = cart.find((item) => item.id === id);
    if (existing) existing.qty = Math.min(existing.qty + 1, product.stock);
    else cart.push({ id, name: product.name, price: Number(product.price) || 0, qty: 1, stock: product.stock });
    renderCart(); renderProducts();
  }
  function removeFromCart(id) { cart = cart.filter((item) => item.id !== id); renderCart(); renderProducts(); }
  function updateQty(id, delta) {
    const item = cart.find((entry) => entry.id === id);
    if (!item) return;
    item.qty = Math.max(1, Math.min(item.qty + delta, item.stock));
    renderCart(); renderProducts();
  }
  function renderCart() {
    const area = get("cart-items");
    get("cart-count").textContent = cart.length + " item" + (cart.length === 1 ? "" : "s");
    area.replaceChildren();
    if (!cart.length) area.appendChild(styled(element("div", "", "Cart is empty. Tap a product to add."), "text-align:center;padding:2rem 0.5rem;color:var(--pharma-muted);font-size:0.85rem"));
    cart.forEach((item) => {
      const line = styled(element("div"), "display:flex;gap:0.65rem;padding:0.6rem 0.35rem;border-bottom:1px solid rgba(226,230,227,0.6);align-items:flex-start");
      const details = styled(element("div"), "flex:1;min-width:0");
      details.append(styled(element("div", "", item.name), "font-weight:700;font-size:0.85rem"), styled(element("div", "", money(item.price) + " ea."), "font-size:0.74rem;color:var(--pharma-muted)"));
      const controls = styled(element("div"), "display:flex;align-items:center;gap:0.35rem;margin-top:0.35rem");
      const down = styled(element("button", "", "−"), "width:24px;height:24px;border:1px solid var(--pharma-border);border-radius:50%;background:#fff;cursor:pointer;font-weight:700;display:grid;place-items:center;font-size:0.9rem");
      down.addEventListener("click", () => updateQty(item.id, -1));
      const count = styled(element("span", "", item.qty), "min-width:28px;text-align:center;font-weight:700;font-size:0.88rem");
      const up = styled(element("button", "", "+"), "width:24px;height:24px;border:1px solid var(--pharma-border);border-radius:50%;background:#fff;cursor:pointer;font-weight:700;display:grid;place-items:center;font-size:0.9rem");
      up.addEventListener("click", () => updateQty(item.id, 1));
      controls.append(down, count, up); details.appendChild(controls); line.appendChild(details);
      const summary = styled(element("div"), "text-align:right;flex-shrink:0");
      summary.appendChild(styled(element("div", "", money(item.price * item.qty)), "font-weight:800;font-size:0.9rem"));
      const remove = styled(element("button", "", "Remove"), "background:none;border:none;color:#dc2626;cursor:pointer;font-size:0.72rem;font-weight:600;margin-top:0.3rem;font-family:inherit");
      remove.addEventListener("click", () => removeFromCart(item.id)); summary.appendChild(remove); line.appendChild(summary); area.appendChild(line);
    });
    updateTotals();
  }
  function updateTotals() {
    const subtotal = cart.reduce((sum, item) => sum + item.price * item.qty, 0);
    const discount = Number.parseFloat(get("discount-input").value) || 0;
    const total = Math.max(0, subtotal - discount);
    const cash = Number.parseFloat(get("cash-input").value) || 0;
    get("subtotal-val").textContent = money(subtotal); get("total-val").textContent = money(total);
    get("change-row").style.display = cash > 0 ? "flex" : "none"; get("change-val").textContent = money(Math.max(0, cash - total));
    const button = get("checkout-btn"); button.disabled = !cart.length; button.textContent = "Complete Sale — " + money(total);
  }
  function showReceipt(data) {
    const body = get("receipt-body"); body.replaceChildren();
    const heading = styled(element("div"), "font-size:0.76rem;color:#6b7b8b;display:grid;gap:0.25rem;margin-bottom:0.85rem");
    row(heading, "Transaction", data.transaction_id, "font-weight:700;color:#1f3b53"); row(heading, "Date", data.date); row(heading, "Time", data.time);
    body.append(heading, styled(element("div"), "border-top:1px dashed #cdd8e3;margin:0.85rem 0"));
    const items = styled(element("div"), "display:grid;gap:0.5rem;margin-bottom:0.85rem");
    data.items.forEach((item) => { const itemRow = element("div"); itemRow.appendChild(styled(element("div", "", item.name), "font-weight:700;font-size:0.85rem;color:#1a2b3d;margin-bottom:0.1rem")); const detail = styled(element("div"), "display:flex;justify-content:space-between;font-size:0.8rem"); detail.append(element("span", "", `${item.qty} × ${money(item.price)}`), styled(element("span", "", money(item.qty * Number(item.price))), "font-weight:700")); itemRow.appendChild(detail); items.appendChild(itemRow); });
    body.append(items, styled(element("div"), "border-top:1px dashed #cdd8e3;margin:0.85rem 0"));
    const totals = styled(element("div"), "display:grid;gap:0.3rem;margin-bottom:0.85rem;font-size:0.82rem"); row(totals, "Subtotal", money(data.subtotal)); if (data.discount > 0) row(totals, "Discount", "− " + money(data.discount), "color:#dc2626"); const totalRow = row(totals, "TOTAL", money(data.total), "font-weight:800;font-size:1.05rem;color:var(--pharma-primary)"); totalRow.style.borderTop = "2px solid var(--pharma-primary)"; totalRow.style.paddingTop = "0.35rem"; body.appendChild(totals);
    const payment = styled(element("div"), "background:#f4faf9;border:1px solid #c8e6e3;border-radius:0.85rem;padding:0.85rem 1rem;margin-bottom:1.1rem;font-size:0.82rem;display:grid;gap:0.3rem"); row(payment, "Method", data.method === "gcash" ? "GCASH" : "CASH", "font-weight:700"); if (data.method === "gcash") row(payment, "Reference Number", data.payment_reference, "font-weight:700"); else { row(payment, "Cash Tendered", money(data.cash_given), "font-weight:700"); row(payment, "Change", money(data.change), "font-size:0.9rem;font-weight:800;color:#15803d"); }
    const footer = styled(element("div"), "text-align:center;font-size:0.73rem;color:#9ca3af;line-height:1.7"); footer.append(element("div", "", "Thank you for your purchase!"), styled(element("div", "", "L.A · BIR Accredited"), "margin-top:0.3rem;font-weight:700;color:#6b7b8b")); body.append(payment, footer); get("receipt-modal").style.display = "flex";
  }
  function updatePaymentMethod() { const gcash = get("payment-method").value === "gcash"; get("gcash-reference-wrap").classList.toggle("hidden", !gcash); get("gcash-reference").required = gcash; get("cash-input").disabled = gcash; if (gcash) get("cash-input").value = ""; updateTotals(); }
  document.querySelectorAll(".pos-cat-btn").forEach((button) => button.addEventListener("click", () => { category = button.dataset.cat; document.querySelectorAll(".pos-cat-btn").forEach((item) => item.classList.toggle("active", item.dataset.cat === category)); renderProducts(); }));
  get("search-input").addEventListener("input", (event) => { query = event.target.value.toLowerCase(); renderProducts(); }); get("discount-input").addEventListener("input", updateTotals); get("cash-input").addEventListener("input", updateTotals); get("gcash-reference").addEventListener("input", (event) => { event.target.value = event.target.value.replace(/\D/g, ""); }); get("payment-method").addEventListener("change", updatePaymentMethod);
  get("checkout-btn").addEventListener("click", async () => { if (!cart.length) return; const method = get("payment-method").value; const reference = get("gcash-reference").value.trim(); if (method === "gcash" && !reference) { get("gcash-reference").focus(); alert("Please enter the GCash reference number."); return; } try { const response = await fetch(checkoutUrl, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken }, body: JSON.stringify({ cart: cart.map((item) => ({ id: item.id, qty: item.qty })), discount: Number.parseFloat(get("discount-input").value) || 0, cash_given: Number.parseFloat(get("cash-input").value) || 0, method, payment_reference: reference, idempotency_key: crypto.randomUUID() }) }); const data = await response.json(); if (!data.success) { alert("Checkout failed: " + (data.error || "Unknown error")); return; } showReceipt(data); cart = []; get("discount-input").value = ""; get("cash-input").value = ""; get("gcash-reference").value = ""; get("payment-method").value = "cash"; updatePaymentMethod(); renderCart(); renderProducts(); } catch (error) { alert("Network error: " + error.message); } });
  get("receipt-modal")?.addEventListener("click", (event) => { if (event.target.id === "receipt-modal") get("receipt-modal").style.display = "none"; }); document.querySelector(".js-close-receipt")?.addEventListener("click", () => { get("receipt-modal").style.display = "none"; }); document.querySelector(".js-print-receipt")?.addEventListener("click", () => window.print());
  window.POS = { addToCart, removeFromCart, updateQty, clearCart: () => { cart = []; renderCart(); renderProducts(); } };
  renderProducts(); renderCart();
})();
