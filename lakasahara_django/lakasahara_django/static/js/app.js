document.addEventListener("DOMContentLoaded", () => {
  window.currentEditProductId = null;
  window.currentDeleteProductId = null;

  const notificationMenu = document.querySelector(".notification-menu");
  const notificationTrigger = document.querySelector(".notification-trigger");
  const notificationPanel = document.querySelector(".notification-panel");
  const notificationClose = document.querySelector(".notification-close");
  const closeNotifications = () => {
    if (!notificationPanel || !notificationTrigger) return;
    notificationPanel.classList.remove("is-open");
    notificationPanel.setAttribute("aria-hidden", "true");
    notificationTrigger.setAttribute("aria-expanded", "false");
  };
  notificationTrigger?.addEventListener("click", () => {
    if (!notificationPanel) return;
    const isOpen = notificationPanel.classList.toggle("is-open");
    notificationPanel.setAttribute("aria-hidden", String(!isOpen));
    notificationTrigger.setAttribute("aria-expanded", String(isOpen));
  });
  notificationClose?.addEventListener("click", closeNotifications);
  document.addEventListener("click", (event) => {
    if (notificationMenu && !notificationMenu.contains(event.target)) closeNotifications();
  });

  document.querySelectorAll(".js-toggle-password").forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.dataset.target;
      const field = document.getElementById(targetId);
      if (!field) return;
      field.type = field.type === "password" ? "text" : "password";
    });
  });

  document.querySelectorAll(".js-toggle-batches").forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.dataset.targetId;
      const row = document.getElementById(targetId);
      if (!row) return;
      const isHidden = row.style.display === "none" || !row.style.display;
      row.style.display = isHidden ? "table-row" : "none";
      document
        .querySelectorAll(`[data-target-id="${targetId}"]`)
        .forEach((toggle) =>
          toggle.setAttribute("aria-expanded", String(isHidden)),
        );
    });
  });

  document.querySelectorAll(".js-toggle-details").forEach((button) => {
    button.addEventListener("click", () => {
      const allDetailCols = document.querySelectorAll(".detail-col");
      const isVisible = button.dataset.expanded === "true";
      allDetailCols.forEach((col) =>
        col.classList.toggle("visible", !isVisible),
      );
      button.dataset.expanded = String(!isVisible);
      button.textContent = isVisible ? "Show Details" : "Hide Details";
    });
  });

  document.querySelectorAll(".js-filter-submit").forEach((select) => {
    select.addEventListener("change", () => {
      if (select.form) {
        select.form.submit();
      }
    });
  });

  document.querySelectorAll(".js-open-modal").forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.dataset.modalTarget;
      const modal = targetId ? document.getElementById(targetId) : null;
      if (modal) {
        modal.classList.add("active");
      }
    });
  });

  document.querySelectorAll(".js-open-product-modal").forEach((button) => {
    button.addEventListener("click", () => {
      const modal = document.getElementById("product-modal");
      if (!modal) return;

      const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value || "-";
      };

      setText("product-modal-title", button.dataset.productName || "Product");
      setText("product-modal-category", button.dataset.productCategory);
      setText("product-modal-kind", button.dataset.productKind);
      setText("product-modal-type", button.dataset.productType);
      setText("product-modal-price", button.dataset.productPrice ? `PHP ${button.dataset.productPrice}` : "-");
      setText("product-modal-stock", button.dataset.productStock ? `${button.dataset.productStock} units` : "-");
      setText("product-modal-barcode", button.dataset.productBarcode);
      setText("product-modal-shelf", button.dataset.productShelf);
      modal.classList.add("active");
      modal.setAttribute("aria-hidden", "false");
    });
  });

  document.querySelectorAll(".js-close-modal").forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.dataset.modalTarget;
      const modal = targetId ? document.getElementById(targetId) : null;
      if (modal) {
        modal.classList.remove("active");
        modal.setAttribute("aria-hidden", "true");
      }
    });
  });

  const productModal = document.getElementById("product-modal");
  if (productModal) {
    productModal.addEventListener("click", (event) => {
      if (event.target === productModal) {
        productModal.classList.remove("active");
        productModal.setAttribute("aria-hidden", "true");
      }
    });
  }

  document.querySelectorAll(".js-open-edit-modal").forEach((button) => {
    button.addEventListener("click", () => {
      const productId = button.dataset.productId;
      const modal = document.getElementById("editModal");
      if (!modal || !productId) return;
      modal.classList.add("active");
      const form = document.getElementById("editProductForm");
      if (!form) return;

      fetch(`/products/${productId}/edit-form/`, {
        method: "GET",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((response) => response.json())
        .then((data) => {
          const content = document.getElementById("editFormContent");
          if (!content) return;
          const grid = document.createElement("div");
          grid.className = "grid-2";
          data.fields.forEach((field) => {
            const group = document.createElement("div");
            group.className = "form-group";
            if (field.name === "name" || field.name === "image_url") group.style.gridColumn = "1/-1";
            const label = document.createElement("label");
            label.className = "form-label";
            label.htmlFor = field.id;
            label.textContent = field.label;
            group.appendChild(label);
            let input;
            if (field.input_type === "select") {
              input = document.createElement("select");
              field.choices.forEach(([value, labelText]) => {
                const option = document.createElement("option");
                option.value = value;
                option.textContent = labelText;
                option.selected = String(value) === String(field.value);
                input.appendChild(option);
              });
            } else if (field.input_type === "textarea") {
              input = document.createElement("textarea");
              input.value = field.value;
            } else {
              input = document.createElement("input");
              input.type = field.input_type || "text";
              input.value = field.value;
            }
            input.name = field.name;
            input.id = field.id;
            input.className = "form-control";
            group.appendChild(input);
            field.errors.forEach((errorText) => {
              const error = document.createElement("div");
              error.style.cssText = "color:var(--pharma-danger);font-size:0.8rem;margin-top:0.3rem";
              error.textContent = errorText;
              group.appendChild(error);
            });
            grid.appendChild(group);
          });
          content.replaceChildren(grid);
        })
        .catch(() => {
          const content = document.getElementById("editFormContent");
          if (!content) return;
          const error = document.createElement("p");
          error.style.color = "red";
          error.textContent = "Error loading form";
          content.replaceChildren(error);
        });

      form.dataset.currentProductId = productId;
      window.currentEditProductId = Number(productId);
    });
  });

  const editModal = document.getElementById("editModal");
  const deleteModal = document.getElementById("deleteModal");
  if (editModal) {
    editModal.addEventListener("click", (event) => {
      if (event.target === editModal) {
        editModal.classList.remove("active");
      }
    });
  }
  if (deleteModal) {
    deleteModal.addEventListener("click", (event) => {
      if (event.target === deleteModal) {
        deleteModal.classList.remove("active");
      }
    });
  }

  const editForm = document.getElementById("editProductForm");
  if (editForm) {
    editForm.addEventListener("submit", (event) => {
      const productId = window.currentEditProductId;
      if (!productId) return;
      event.preventDefault();
      const formData = new FormData(event.target);
      fetch(`/products/${productId}/edit/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": formData.get("csrfmiddlewaretoken"),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            window.alert("Product updated successfully!");
            window.location.reload();
          } else {
            window.alert(
              "Error updating product: " + (data.error || "Unknown error"),
            );
          }
        })
        .catch(() => {
          window.alert("Error updating product");
        });
    });
  }

  document.querySelectorAll(".js-open-delete-modal").forEach((button) => {
    button.addEventListener("click", () => {
      const modal = document.getElementById("deleteModal");
      if (!modal) return;
      document.getElementById("deleteProductName").textContent =
        button.dataset.productName || "-";
      document.getElementById("deleteProductBarcode").textContent =
        button.dataset.productBarcode || "-";
      document.getElementById("deleteProductSupplier").textContent =
        button.dataset.productSupplier || "—";
      document.getElementById("deleteProductStock").textContent =
        (button.dataset.productStock || "0") + " units";
      window.currentDeleteProductId = button.dataset.productId;
      modal.classList.add("active");
    });
  });

  const confirmDeleteButton = document.getElementById("confirmDeleteButton");
  if (confirmDeleteButton) {
    confirmDeleteButton.addEventListener("click", () => {
      const productId = window.currentDeleteProductId;
      if (!productId) return;
      const form = document.createElement("form");
      form.method = "POST";
      form.action = "/products/" + productId + "/delete/";
      const csrfToken =
        document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
        document.cookie
          .split("; ")
          .find((row) => row.startsWith("csrftoken="))
          ?.split("=")[1];
      if (csrfToken) {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "csrfmiddlewaretoken";
        input.value = csrfToken;
        form.appendChild(input);
      }
      document.body.appendChild(form);
      form.submit();
    });
  }

  document.querySelectorAll(".js-open-user-delete-modal").forEach((button) => {
    button.addEventListener("click", () => {
      const modal = document.getElementById("delete-user-modal");
      if (!modal) return;

      const userName = button.dataset.userName || "User";
      const username = button.dataset.userUsername || "username";
      const initials = (userName || username || "U")
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase() || "")
        .join("") || "U";

      document.getElementById("delete-user-name").textContent = userName;
      document.getElementById("delete-user-username").textContent = `@${username}`;
      document.getElementById("delete-user-avatar").textContent = initials;
      document.getElementById("delete-user-id").value = button.dataset.userId || "";

      modal.classList.add("active");
      modal.setAttribute("aria-hidden", "false");
    });
  });

  const deleteUserForm = document.getElementById("delete-user-form");
  if (deleteUserForm) {
    deleteUserForm.addEventListener("submit", (event) => {
      const userId = document.getElementById("delete-user-id")?.value;
      if (!userId) {
        event.preventDefault();
        return;
      }
      if (!window.confirm("Are you sure you want to delete this user? This cannot be undone.")) {
        event.preventDefault();
      }
    });
  }

  const receiptModal = document.getElementById("receipt-modal");
  if (receiptModal) {
    receiptModal.addEventListener("click", (event) => {
      if (event.target === receiptModal) {
        receiptModal.style.display = "none";
      }
    });
  }

  document.querySelectorAll(".js-close-receipt").forEach((button) => {
    button.addEventListener("click", () => {
      const modal = document.getElementById("receipt-modal");
      if (modal) modal.style.display = "none";
    });
  });

  const clearCartButton = document.querySelector(".js-clear-cart");
  if (clearCartButton && window.POS) {
    clearCartButton.addEventListener("click", () => window.POS.clearCart());
  }

  const queueCheckboxes = document.querySelectorAll(".pharmacist-queue-checkbox");
  const approveSelectedButton = document.querySelector(".pharmacist-approve-button");
  if (queueCheckboxes.length && approveSelectedButton) {
    const updateApprovalCount = () => {
      const selectedCount = document.querySelectorAll(
        ".pharmacist-queue-checkbox:checked",
      ).length;
      approveSelectedButton.textContent = `Approve Selected (${selectedCount})`;
      approveSelectedButton.disabled = selectedCount === 0;
      approveSelectedButton.classList.toggle("has-selection", selectedCount > 0);
      queueCheckboxes.forEach((checkbox) =>
        checkbox.closest(".pharmacist-queue-item")?.classList.toggle(
          "is-selected",
          checkbox.checked,
        ),
      );
    };
    queueCheckboxes.forEach((checkbox) =>
      checkbox.addEventListener("change", updateApprovalCount),
    );
    approveSelectedButton.addEventListener("click", () => {
      const modal = document.getElementById("approval-modal");
      const selectedItems = modal?.querySelector(".approval-selected-list");
      const selected = [...document.querySelectorAll(".pharmacist-queue-checkbox:checked")];
      if (!modal || !selectedItems || !selected.length) return;
      selectedItems.replaceChildren(
        ...selected.map((checkbox) => {
          const item = document.createElement("li");
          item.textContent = checkbox.dataset.productName || "";
          return item;
        }),
      );
      modal.classList.add("is-open");
      modal.setAttribute("aria-hidden", "false");
    });

    document.querySelectorAll(".approval-modal-close").forEach((button) => {
      button.addEventListener("click", () => {
        const modal = document.getElementById("approval-modal");
        if (!modal) return;
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
      });
    });
    document.getElementById("approval-modal")?.addEventListener("click", (event) => {
      if (event.target.id !== "approval-modal") return;
      event.currentTarget.classList.remove("is-open");
      event.currentTarget.setAttribute("aria-hidden", "true");
    });
    updateApprovalCount();
  }
});
