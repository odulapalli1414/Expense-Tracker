document.addEventListener("DOMContentLoaded", () => {
  // ===== Common elements =====
  const form = document.getElementById("expense-form");
  const submitBtn = document.getElementById("submitBtn");
  const toastEl = document.getElementById("toast");

  function showToast(message, isSuccess) {
    toastEl.textContent = message;
    toastEl.classList.remove("error");
    if (!isSuccess) {
      toastEl.classList.add("error");
    }
    toastEl.classList.add("show");
    setTimeout(() => {
      toastEl.classList.remove("show");
    }, 3000);
  }

  // ===== Expense vs Income toggle =====
  const typeToggle = document.getElementById("typeToggle");
  const entryTypeInput = document.getElementById("entryType");
  const expenseWrapper = document.getElementById("expenseWrapper");
  const incomeSection = document.getElementById("incomeSection");

  typeToggle.addEventListener("click", (e) => {
    const option = e.target.closest(".toggle-option");
    if (!option) return;

    const t = option.getAttribute("data-type"); // "expense" or "income"

    typeToggle.querySelectorAll(".toggle-option").forEach((el) => {
      el.classList.toggle("active", el === option);
    });

    entryTypeInput.value = t;

    if (t === "expense") {
      expenseWrapper.classList.remove("hidden");
      incomeSection.classList.add("hidden");
    } else {
      expenseWrapper.classList.add("hidden");
      incomeSection.classList.remove("hidden");
    }
  });

  // ===== Expense: references =====
  const paymentModeSelect = document.getElementById("paymentMode");
  const cardFields = document.getElementById("cardFields");
  const upiFields = document.getElementById("upiFields");
  const amountDisplay = document.getElementById("amountDisplay");
  const amountHidden = document.getElementById("amount");
  const modeToggle = document.getElementById("modeToggle");
  const entryModeInput = document.getElementById("entryMode");
  const singleSection = document.getElementById("singleSection");
  const bulkSection = document.getElementById("bulkSection");
  const cardTypeSelect = document.getElementById("cardType");
  const cardBankSelect = document.getElementById("cardBankName");

  // Bulk controls
  const bulkPaymentModeSelect = document.getElementById("bulkPaymentMode");
  const bulkCardFields = document.getElementById("bulkCardFields");
  const bulkUpiFields = document.getElementById("bulkUpiFields");
  const bulkCardTypeSelect = document.getElementById("bulkCardType");
  const bulkCardBankSelect = document.getElementById("bulkCardBankName");
  const bulkUpiProviderSelect = document.getElementById("bulkUpiProvider");
  const bulkUpiBankSelect = document.getElementById("bulkUpiBankName");
  const bulkUpiCardTypeSelect = document.getElementById("bulkUpiCardType");
  const bulkRowsContainer = document.getElementById("bulkRows");
  const addBulkRowBtn = document.getElementById("addBulkRowBtn");

  let bulkRowCounter = 0;

  // ===== Income: references =====
  const incomeSourceSelect = document.getElementById("incomeSource");
  const incomeAmountDisplay = document.getElementById("incomeAmountDisplay");
  const incomeAmountHidden = document.getElementById("incomeAmount");

  // ===== Amount formatting =====
  function formatWithCommas(value) {
    const numeric = value.replace(/[^0-9.]/g, "");
    if (!numeric) return "";
    const parts = numeric.split(".");
    const intPart = parts[0];
    const decPart = parts.length > 1 ? "." + parts[1] : "";
    const intFormatted = Number(intPart).toLocaleString("en-US");
    return intFormatted + decPart;
  }

  amountDisplay.addEventListener("input", () => {
    const raw = amountDisplay.value;
    const numeric = raw.replace(/[^0-9.]/g, "");
    amountHidden.value = numeric;
    amountDisplay.value = formatWithCommas(raw);
  });

  incomeAmountDisplay.addEventListener("input", () => {
    const raw = incomeAmountDisplay.value;
    const numeric = raw.replace(/[^0-9.]/g, "");
    incomeAmountHidden.value = numeric;
    incomeAmountDisplay.value = formatWithCommas(raw);
  });

  function attachAmountFormatter(displayInput, hiddenInput) {
    displayInput.addEventListener("input", () => {
      const raw = displayInput.value;
      const numeric = raw.replace(/[^0-9.]/g, "");
      hiddenInput.value = numeric;
      displayInput.value = formatWithCommas(raw);
    });
  }

  // ===== Expense: Payment mode conditional fields =====
  paymentModeSelect.addEventListener("change", () => {
    const mode = paymentModeSelect.value;
    cardFields.classList.add("hidden");
    upiFields.classList.add("hidden");

    if (mode === "Card") {
      cardFields.classList.remove("hidden");
    } else if (mode === "UPI") {
      upiFields.classList.remove("hidden");
    }
  });

  // Single: Card Type -> Bank options
  cardTypeSelect.addEventListener("change", () => {
    const type = cardTypeSelect.value;
    cardBankSelect.innerHTML = "<option value=''>Select...</option>";
    if (type === "Debit") {
      ["SBI 81", "HDFC 84"].forEach((b) => {
        const opt = document.createElement("option");
        opt.value = b;
        opt.textContent = b;
        cardBankSelect.appendChild(opt);
      });
    } else if (type === "Credit") {
      ["HDFC 78", "HDFC 45"].forEach((b) => {
        const opt = document.createElement("option");
        opt.value = b;
        opt.textContent = b;
        cardBankSelect.appendChild(opt);
      });
    }
  });

  // Bulk: Payment mode conditional fields
  bulkPaymentModeSelect.addEventListener("change", () => {
    const mode = bulkPaymentModeSelect.value;
    bulkCardFields.classList.add("hidden");
    bulkUpiFields.classList.add("hidden");

    if (mode === "Card") {
      bulkCardFields.classList.remove("hidden");
    } else if (mode === "UPI") {
      bulkUpiFields.classList.remove("hidden");
    }
  });

  // Bulk: Card Type -> Bank options
  bulkCardTypeSelect.addEventListener("change", () => {
    const type = bulkCardTypeSelect.value;
    bulkCardBankSelect.innerHTML = "<option value=''>Select...</option>";
    if (type === "Debit") {
      ["SBI 81", "HDFC 84"].forEach((b) => {
        const opt = document.createElement("option");
        opt.value = b;
        opt.textContent = b;
        bulkCardBankSelect.appendChild(opt);
      });
    } else if (type === "Credit") {
      ["HDFC 78", "HDFC 45"].forEach((b) => {
        const opt = document.createElement("option");
        opt.value = b;
        opt.textContent = b;
        bulkCardBankSelect.appendChild(opt);
      });
    }
  });

  // ===== Bulk row creation/removal =====
  function createBulkRow() {
    bulkRowCounter += 1;

    const row = document.createElement("div");
    row.className = "bulk-row";

    row.innerHTML = `
      <div>
        <input
          type="text"
          name="bulkItem[]"
          class="bulk-item"
          placeholder="Coffee"
        />
      </div>
      <div>
        <select name="bulkCategory[]" class="bulk-category">
          <option value="">Select...</option>
          <option value="Bills">Bills</option>
          <option value="Subscriptions">Subscriptions</option>
          <option value="Entertainment">Entertainment</option>
          <option value="Food & Drink">Food & Drink</option>
          <option value="Groceries">Groceries</option>
          <option value="Health & Wellbeing">Health & Wellbeing</option>
          <option value="Other">Other</option>
          <option value="Shopping">Shopping</option>
          <option value="Transport">Transport</option>
          <option value="Travel">Travel</option>
          <option value="Business">Business</option>
          <option value="Gifts">Gifts</option>
        </select>
      </div>
      <div>
        <input
          type="text"
          class="bulk-amount-display"
          placeholder="1,234"
        />
        <input
          type="hidden"
          name="bulkAmount[]"
          class="bulk-amount"
        />
      </div>
      <div>
        <input
          type="text"
          name="bulkRemarks[]"
          class="bulk-remarks"
          placeholder="Optional"
        />
      </div>
      <div class="bulk-row-actions">
        <button type="button" class="remove-row-btn">✕</button>
      </div>
    `;

    const displayInput = row.querySelector(".bulk-amount-display");
    const hiddenInput = row.querySelector(".bulk-amount");
    attachAmountFormatter(displayInput, hiddenInput);

    const removeBtn = row.querySelector(".remove-row-btn");
    removeBtn.addEventListener("click", () => {
      bulkRowsContainer.removeChild(row);
    });

    bulkRowsContainer.appendChild(row);
  }

  // Start with one bulk row
  createBulkRow();

  addBulkRowBtn.addEventListener("click", () => {
    createBulkRow();
  });

  // ===== Single vs Bulk toggle (expense only) =====
  modeToggle.addEventListener("click", (e) => {
    const option = e.target.closest(".toggle-option");
    if (!option) return;
    const mode = option.getAttribute("data-mode");

    modeToggle.querySelectorAll(".toggle-option").forEach((el) => {
      el.classList.toggle("active", el === option);
    });

    entryModeInput.value = mode;

    if (mode === "single") {
      singleSection.classList.remove("muted");
      bulkSection.classList.add("hidden");
      singleSection.querySelectorAll("input, select").forEach((el) => {
        el.disabled = false;
      });
    } else {
      singleSection.classList.add("muted");
      bulkSection.classList.remove("hidden");
      singleSection.querySelectorAll("input, select").forEach((el) => {
        el.disabled = true;
      });
    }
  });

  // ===== Frontend validation =====
  function validateFormFrontend() {
    const entryType = entryTypeInput.value;
    const missing = [];

    if (entryType === "expense") {
      const mode = entryModeInput.value;

      if (mode === "single") {
        const item = (form.item.value || "").trim();
        const category = (form.category.value || "").trim();
        const amount = (amountHidden.value || "").trim();
        const paymentMode = (paymentModeSelect.value || "").trim();

        if (!item) missing.push("Item");
        if (!category) missing.push("Category");
        if (!amount) missing.push("Amount");
        if (!paymentMode) missing.push("Payment Mode");

        if (paymentMode === "Card") {
          const ct = (cardTypeSelect.value || "").trim();
          const cb = (cardBankSelect.value || "").trim();
          if (!ct) missing.push("Card Type (Card)");
          if (!cb) missing.push("Bank (Card)");
        } else if (paymentMode === "UPI") {
          const upiProvider = (form.upiProvider.value || "").trim();
          const upiBank = (form.upiBankName.value || "").trim();
          const upiCardType = (form.upiCardType.value || "").trim();
          if (!upiProvider) missing.push("UPI Provider");
          if (!upiBank) missing.push("Bank (UPI)");
          if (!upiCardType) missing.push("Card Type (UPI)");
        }
      } else {
        const bulkPaymentMode = (bulkPaymentModeSelect.value || "").trim();
        if (!bulkPaymentMode) missing.push("Bulk Payment Mode");

        if (bulkPaymentMode === "Card") {
          const ct = (bulkCardTypeSelect.value || "").trim();
          const cb = (bulkCardBankSelect.value || "").trim();
          if (!ct) missing.push("Bulk Card Type (Card)");
          if (!cb) missing.push("Bulk Bank (Card)");
        } else if (bulkPaymentMode === "UPI") {
          const upiProvider = (bulkUpiProviderSelect.value || "").trim();
          const upiBank = (bulkUpiBankSelect.value || "").trim();
          const upiCardType = (bulkUpiCardTypeSelect.value || "").trim();
          if (!upiProvider) missing.push("Bulk UPI Provider");
          if (!upiBank) missing.push("Bulk Bank (UPI)");
          if (!upiCardType) missing.push("Bulk Card Type (UPI)");
        }

        const rows = Array.from(
          bulkRowsContainer.querySelectorAll(".bulk-row")
        );
        if (rows.length === 0) {
          missing.push("At least one bulk row");
        }
      }
    } else {
      // INCOME
      const src = (incomeSourceSelect.value || "").trim();
      const amt = (incomeAmountHidden.value || "").trim();
      if (!src) missing.push("Income Source");
      if (!amt) missing.push("Income Amount");
    }

    return missing;
  }

  // ===== AJAX submit with error handling =====
  form.addEventListener("submit", (e) => {
    e.preventDefault();

    const missing = validateFormFrontend();
    if (missing.length > 0) {
      const msg = "Missing fields:\n- " + missing.join("\n- ");
      showToast(msg, false);
      return;
    }

    submitBtn.disabled = true;
    const formData = new FormData(form);

    fetch("/add", {
      method: "POST",
      body: formData,
    })
      .then(async (res) => {
        let data;
        try {
          data = await res.json();
        } catch {
          showToast("Fields did not update in the sheets.", false);
          return;
        }

        if (data.success) {
          showToast("Fields updated in the sheets.", true);

          if (entryTypeInput.value === "expense") {
            if (entryModeInput.value === "single") {
              form.item.value = "";
              form.category.value = "";
              amountDisplay.value = "";
              amountHidden.value = "";
              paymentModeSelect.value = "";
              cardTypeSelect.value = "";
              cardBankSelect.innerHTML = "<option value=''>Select...</option>";
              form.upiProvider.value = "";
              form.upiBankName.value = "";
              form.upiCardType.value = "";
              form.purchaseDate.value = "";
              form.remarks.value = "";
              cardFields.classList.add("hidden");
              upiFields.classList.add("hidden");
            } else {
              bulkPaymentModeSelect.value = "";
              bulkCardTypeSelect.value = "";
              bulkCardBankSelect.innerHTML = "<option value=''>Select...</option>";
              bulkUpiProviderSelect.value = "";
              bulkUpiBankSelect.value = "";
              bulkUpiCardTypeSelect.value = "";
              form.bulkPurchaseDate.value = "";
              bulkCardFields.classList.add("hidden");
              bulkUpiFields.classList.add("hidden");
              bulkRowsContainer.innerHTML = "";
              bulkRowCounter = 0;
              createBulkRow();
            }
          } else {
            // Reset income form
            incomeSourceSelect.value = "";
            incomeAmountDisplay.value = "";
            incomeAmountHidden.value = "";
            document.getElementById("incomeDate").value = "";
            document.getElementById("payslip").value = "";
          }
        } else {
          const backendMsg = data.error ? "\n" + data.error : "";
          showToast("Fields did not update in the sheets." + backendMsg, false);
        }
      })
      .catch(() => {
        showToast("Fields did not update in the sheets.", false);
      })
      .finally(() => {
        submitBtn.disabled = false;
      });
  });
});
