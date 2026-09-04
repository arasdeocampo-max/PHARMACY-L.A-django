/* Inventory Monitor batch row controls. */
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".inv-toggle-btn").forEach(function (button) {
    button.addEventListener("click", function (event) {
      event.stopPropagation();
      toggleBatches(button.dataset.product);
    });
  });

  document.querySelectorAll(".inv-product-row").forEach(function (row) {
    row.addEventListener("click", function () {
      toggleBatches(row.dataset.product);
    });
  });

  document.querySelectorAll(".inv-stop-prop").forEach(function (element) {
    element.addEventListener("click", function (event) {
      event.stopPropagation();
    });
  });

  document.querySelectorAll(".inv-details-btn, .inv-modal-trigger, .inv-modal-close").forEach(function (button) {
    button.addEventListener("click", function (event) {
      event.stopPropagation();
      var modal = document.getElementById(button.dataset.modalTarget);
      if (!modal) return;
      var isOpen = modal.getAttribute("aria-hidden") === "false";
      modal.setAttribute("aria-hidden", String(isOpen));
      modal.classList.toggle("is-open", !isOpen);
    });
  });

  document.querySelectorAll(".inventory-modal-overlay").forEach(function (modal) {
    modal.addEventListener("click", function (event) {
      if (event.target === modal) {
        modal.setAttribute("aria-hidden", "true");
        modal.classList.remove("is-open");
      }
    });
  });

  var openBatchId = new URLSearchParams(window.location.search).get("open_batch");
  if (openBatchId) {
    toggleBatches(openBatchId);
  }
});

function toggleBatches(id) {
  var batchRow = document.getElementById("batches-" + id);
  var chevron = document.getElementById("chev-" + id);

  if (!batchRow) return;

  var isOpen = batchRow.style.display === "table-row";
  batchRow.style.display = isOpen ? "none" : "table-row";

  document.querySelectorAll('[data-product="' + id + '"]').forEach(function (control) {
    control.setAttribute("aria-expanded", String(!isOpen));
  });

  if (chevron) {
    chevron.textContent = isOpen ? "›" : "⌄";
  }
}