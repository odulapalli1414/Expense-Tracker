const tableDiv = document.getElementById("table");
const tabs = document.querySelectorAll(".tab");

const overlay = document.getElementById("overlay");
const modalTitle = document.getElementById("modalTitle");
const modalBody = document.getElementById("modalBody");
const saveBtn = document.getElementById("saveBtn");

let currentType = "expenses";
let dataCache = [];
let editId = null;

tabs.forEach(t => {
  t.onclick = () => {
    tabs.forEach(x => x.classList.remove("active"));
    t.classList.add("active");
    currentType = t.dataset.type;
    load();
  };
});

function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${days[d.getDay()]}, ${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
}

// Custom modal
function showModal(title, message, type = 'info', onConfirm = null) {
  const modal = document.createElement('div');
  modal.className = 'custom-modal-overlay';
  
  const iconMap = {
    'info': '💡',
    'success': '✅',
    'warning': '⚠️',
    'error': '❌',
    'confirm': '❓'
  };
  
  const icon = iconMap[type] || '💡';
  
  modal.innerHTML = `
    <div class="custom-modal ${type}">
      <div class="custom-modal-icon">${icon}</div>
      <h3 class="custom-modal-title">${title}</h3>
      <p class="custom-modal-message">${message}</p>
      <div class="custom-modal-buttons">
        ${onConfirm ? '<button class="modal-btn confirm-btn" id="confirmBtn">Confirm</button>' : ''}
        <button class="modal-btn cancel-btn" id="cancelBtn">${onConfirm ? 'Cancel' : 'OK'}</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  setTimeout(() => modal.classList.add('show'), 10);
  
  const confirmBtn = modal.querySelector('#confirmBtn');
  const cancelBtn = modal.querySelector('#cancelBtn');
  
  const closeModal = () => {
    modal.classList.remove('show');
    setTimeout(() => document.body.removeChild(modal), 300);
  };
  
  if (confirmBtn) {
    confirmBtn.onclick = () => {
      closeModal();
      if (onConfirm) onConfirm();
    };
  }
  
  cancelBtn.onclick = closeModal;
}

async function load() {
  const res = await fetch(`/api/${currentType}`);
  dataCache = await res.json();

  let html = "<table><tr>";

  if (currentType === "expenses") {
    html += "<th>#</th><th>Item</th><th>Amount</th><th>Payment</th><th>Date</th><th>Actions</th>";
  } else {
    html += "<th>#</th><th>Source</th><th>Amount</th><th>Date</th><th>Payslip</th><th>Actions</th>";
  }

  html += "</tr>";

  dataCache.forEach((r, index) => {
    html += "<tr>";

    if (currentType === "expenses") {
      let payment = r.payment_mode;
      if (r.payment_mode !== "Cash" && r.bank_name) {
        payment = `${r.payment_mode} (${r.bank_name})`;
      }

      html += `
        <td class="index-cell">${index + 1}</td>
        <td>${r.item}</td>
        <td>₹${r.amount}</td>
        <td>${payment}</td>
        <td>${formatDate(r.purchase_date)}</td>
      `;
    } else {
      const payslipBtn = r.payslip_url 
        ? `<a href="${r.payslip_url}" target="_blank" download class="download-btn">📥 Download</a>`
        : '<span style="color:#6b7280">—</span>';
      
      html += `
        <td class="index-cell">${index + 1}</td>
        <td>${r.source}</td>
        <td>₹${r.amount}</td>
        <td>${formatDate(r.income_date)}</td>
        <td>${payslipBtn}</td>
      `;
    }

    html += `
      <td class="actions">
        <button onclick="view(${r.id})" class="action-btn view-btn" title="View Details">👁</button>
        <button onclick="edit(${r.id})" class="action-btn edit-btn" title="Edit Entry">✏️</button>
        <button onclick="del(${r.id})" class="action-btn delete-btn" title="Delete Entry">🗑</button>
      </td>
    </tr>`;
  });

  html += "</table>";
  tableDiv.innerHTML = html;
}

function view(id) {
  const r = dataCache.find(x => x.id === id);
  modalTitle.textContent = "View Entry";
  saveBtn.classList.add("hidden");

  let content = `<p><b>Amount:</b> ₹${r.amount}</p>`;
  
  if (currentType === "expenses") {
    content += `<p><b>Item:</b> ${r.item}</p>`;
    content += `<p><b>Category:</b> ${r.category || 'N/A'}</p>`;
    content += `<p><b>Payment:</b> ${r.payment_mode}${r.bank_name ? " (" + r.bank_name + ")" : ""}</p>`;
    content += `<p><b>Date:</b> ${formatDate(r.purchase_date)}</p>`;
    if (r.remarks) content += `<p><b>Remarks:</b> ${r.remarks}</p>`;
  } else {
    content += `<p><b>Source:</b> ${r.source}</p>`;
    content += `<p><b>Date:</b> ${formatDate(r.income_date)}</p>`;
    if (r.payslip_url) {
      content += `<p><b>Payslip:</b> <a href="${r.payslip_url}" target="_blank" download class="download-btn-modal">📥 Download PDF</a></p>`;
    }
  }

  modalBody.innerHTML = content;
  overlay.classList.remove("hidden");
}

function edit(id) {
  const r = dataCache.find(x => x.id === id);
  editId = id;

  modalTitle.textContent = "Edit Entry";
  saveBtn.classList.remove("hidden");

  if (currentType === "expenses") {
    modalBody.innerHTML = `
      <label>Item</label>
      <input id="editItem" placeholder="Item" value="${r.item || ''}">
      
      <label>Amount</label>
      <input id="editAmount" placeholder="Amount" value="${r.amount || ''}">
      
      <label>Payment Mode</label>
      <select id="editPaymentMode">
        <option value="Cash" ${r.payment_mode === 'Cash' ? 'selected' : ''}>Cash</option>
        <option value="Card" ${r.payment_mode === 'Card' ? 'selected' : ''}>Card</option>
        <option value="UPI" ${r.payment_mode === 'UPI' ? 'selected' : ''}>UPI</option>
      </select>
      
      <div id="editCardFields" class="hidden">
        <label>Card Type</label>
        <select id="editCardType">
          <option value="">Select...</option>
          <option value="Credit" ${r.card_type === 'Credit' ? 'selected' : ''}>Credit</option>
          <option value="Debit" ${r.card_type === 'Debit' ? 'selected' : ''}>Debit</option>
        </select>
        
        <label>Bank</label>
        <select id="editCardBank">
          <option value="">Select...</option>
        </select>
      </div>
      
      <div id="editUpiFields" class="hidden">
        <label>UPI Provider</label>
        <select id="editUpiProvider">
          <option value="">Select...</option>
          <option value="GPay">GPay</option>
          <option value="PhonePe">PhonePe</option>
          <option value="Paytm">Paytm</option>
          <option value="Others">Others</option>
        </select>
        
        <label>Bank</label>
        <select id="editUpiBank">
          <option value="">Select...</option>
          <option value="SBI 1234">SBI 1234</option>
          <option value="HDFC 4563">HDFC 4563</option>
          <option value="ICICI 7890">ICICI 7890</option>
          <option value="Axis 1122">Axis 1122</option>
          <option value="Other">Other</option>
        </select>
        
        <label>Card Type</label>
        <select id="editUpiCardType">
          <option value="">Select...</option>
          <option value="Credit" ${r.card_type === 'Credit' ? 'selected' : ''}>Credit</option>
          <option value="Debit" ${r.card_type === 'Debit' ? 'selected' : ''}>Debit</option>
        </select>
      </div>
      
      <label>Remarks</label>
      <input id="editRemarks" placeholder="Remarks" value="${r.remarks || ''}">
    `;

    const paymentModeSelect = document.getElementById("editPaymentMode");
    const cardFields = document.getElementById("editCardFields");
    const upiFields = document.getElementById("editUpiFields");
    const cardTypeSelect = document.getElementById("editCardType");
    const cardBankSelect = document.getElementById("editCardBank");

    function updatePaymentFields() {
      const mode = paymentModeSelect.value;
      cardFields.classList.add("hidden");
      upiFields.classList.add("hidden");

      if (mode === "Card") {
        cardFields.classList.remove("hidden");
        updateCardBanks();
      } else if (mode === "UPI") {
        upiFields.classList.remove("hidden");
      }
    }

    function updateCardBanks() {
      const type = cardTypeSelect.value;
      cardBankSelect.innerHTML = "<option value=''>Select...</option>";
      
      if (type === "Debit") {
        ["SBI 81", "HDFC 84"].forEach(b => {
          const opt = document.createElement("option");
          opt.value = b;
          opt.textContent = b;
          if (b === r.bank_name) opt.selected = true;
          cardBankSelect.appendChild(opt);
        });
      } else if (type === "Credit") {
        ["HDFC 78", "HDFC 45"].forEach(b => {
          const opt = document.createElement("option");
          opt.value = b;
          opt.textContent = b;
          if (b === r.bank_name) opt.selected = true;
          cardBankSelect.appendChild(opt);
        });
      }
    }

    paymentModeSelect.addEventListener("change", updatePaymentFields);
    cardTypeSelect.addEventListener("change", updateCardBanks);

    updatePaymentFields();

    if (r.payment_mode === "UPI") {
      document.getElementById("editUpiProvider").value = r.upi_provider || "";
      document.getElementById("editUpiBank").value = r.bank_name || "";
      document.getElementById("editUpiCardType").value = r.card_type || "";
    }

  } else {
    modalBody.innerHTML = `
      <label>Source</label>
      <input id="editItem" placeholder="Source" value="${r.source || ''}">
      
      <label>Amount</label>
      <input id="editAmount" placeholder="Amount" value="${r.amount || ''}">
    `;
  }

  saveBtn.onclick = save;
  overlay.classList.remove("hidden");
}

async function save() {
  const data = {
    item: document.getElementById("editItem").value,
    amount: document.getElementById("editAmount").value
  };

  if (currentType === "expenses") {
    const paymentMode = document.getElementById("editPaymentMode").value;
    data.payment_mode = paymentMode;
    data.remarks = document.getElementById("editRemarks").value;

    if (paymentMode === "Card") {
      data.card_type = document.getElementById("editCardType").value;
      data.bank_name = document.getElementById("editCardBank").value;
      data.upi_provider = null;
    } else if (paymentMode === "UPI") {
      data.upi_provider = document.getElementById("editUpiProvider").value;
      data.bank_name = document.getElementById("editUpiBank").value;
      data.card_type = document.getElementById("editUpiCardType").value;
    } else {
      data.card_type = null;
      data.bank_name = null;
      data.upi_provider = null;
    }
  }

  try {
    await fetch(`/api/${currentType}/${editId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });

    closeModal();
    showModal('Success!', 'Entry updated successfully', 'success');
    load();
  } catch (error) {
    showModal('Error', 'Failed to update entry', 'error');
  }
}

async function del(id) {
  showModal(
    'Confirm Deletion',
    'Are you sure you want to delete this entry? This action cannot be undone.',
    'confirm',
    async () => {
      try {
        await fetch(`/api/${currentType}/${id}`, { method: "DELETE" });
        showModal('Deleted!', 'Entry deleted successfully', 'success');
        load();
      } catch (error) {
        showModal('Error', 'Failed to delete entry', 'error');
      }
    }
  );
}

function closeModal() {
  overlay.classList.add("hidden");
  editId = null;
}

load();