// Accounts Page Logic

document.addEventListener('DOMContentLoaded', function () {
  // Initialize
  initializeEventListeners();
  updateStats();
});

function initializeEventListeners() {
  // Modal Outside Click
  window.onclick = function (event) {
    if (event.target.classList.contains('modal')) {
      closeModal(event.target.id);
    }
  };

  // Search & Filter
  const searchInput = document.getElementById('accountSearch');
  if (searchInput) {
    searchInput.addEventListener('keyup', debounce(filterAccounts, 300));
  }

  const statusFilter = document.getElementById('statusFilter');
  if (statusFilter) {
    statusFilter.addEventListener('change', filterAccounts);
  }
}

// --- Modals ---

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = 'block';
    modal.classList.add('fade-in');
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = 'none';
    modal.classList.remove('fade-in');
  }
}

function closeDetailsModal() {
  closeModal('detailsModal');
}

// --- Filtering & Search ---

function filterAccounts() {
  const input = document.getElementById("accountSearch").value.toUpperCase();
  const statusFilter = document.getElementById("statusFilter").value.toUpperCase();
  const rows = document.querySelectorAll(".account-row");

  let visibleCount = 0;

  rows.forEach(row => {
    const username = row.getAttribute("data-username").toUpperCase();
    const proxy = row.getAttribute("data-proxy").toUpperCase();
    const status = row.getAttribute("data-status").toUpperCase();

    const matchSearch = username.indexOf(input) > -1 || proxy.indexOf(input) > -1;
    const matchStatus = statusFilter === "" || status === statusFilter;

    if (matchSearch && matchStatus) {
      row.style.display = "";
      visibleCount++;
    } else {
      row.style.display = "none";
    }
  });

  // Update visible count or show "no results" message if needed
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// --- Bulk Actions ---

function toggleSelectAll() {
  const isChecked = document.getElementById("selectAll").checked;
  const checkboxes = document.querySelectorAll(".account-checkbox");

  checkboxes.forEach(cb => {
    if (cb.closest('tr').style.display !== 'none') {
      cb.checked = isChecked;
    }
  });
  updateBulkActions();
}

function updateBulkActions() {
  const checkedCount = document.querySelectorAll(".account-checkbox:checked").length;
  const bulkActions = document.getElementById("bulkActions");
  const selectedCountSpan = document.getElementById("selectedCount");

  if (selectedCountSpan) selectedCountSpan.innerText = checkedCount;

  if (checkedCount > 0) {
    bulkActions.classList.add("active");
  } else {
    bulkActions.classList.remove("active");
  }
}

async function bulkDelete() {
  if (!confirm("هل أنت متأكد من حذف الحسابات المحددة؟")) return;

  const selectedIds = Array.from(document.querySelectorAll(".account-checkbox:checked")).map(cb => cb.value);

  try {
    const response = await fetch('/delete_accounts_bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: selectedIds })
    });

    const data = await response.json();

    if (data.status === 'success') {
      showToast(data.message, 'success');
      setTimeout(() => location.reload(), 1500);
    } else {
      showToast('خطأ: ' + data.message, 'error');
    }
  } catch (err) {
    console.error(err);
    showToast('حدث خطأ أثناء الاتصال بالخادم', 'error');
  }
}

async function bulkCheckStatus() {
  const selectedIds = Array.from(document.querySelectorAll(".account-checkbox:checked")).map(cb => cb.value);
  if (selectedIds.length === 0) return;

  showToast("جاري بدء الفحص... يرجى الانتظار", 'info');

  try {
    const response = await fetch('/check_accounts_bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: selectedIds })
    });

    const data = await response.json();

    if (data.status === 'success') {
      showToast('تم اكتمال الفحص!', 'success');
      setTimeout(() => location.reload(), 1500);
    } else {
      showToast('خطأ: ' + data.message, 'error');
    }
  } catch (err) {
    console.error(err);
    showToast('حدث خطأ أثناء الاتصال بالخادم', 'error');
  }
}

// --- Single Actions ---

async function checkHealth(accountId, btn) {
  const icon = btn.querySelector('i');
  icon.className = "fas fa-sync-alt fa-spin";

  try {
    const response = await fetch('/check_health/' + accountId, { method: 'POST' });
    const data = await response.json();

    icon.className = "fas fa-sync-alt";

    if (data.status === 'success') {
      showToast('حالة الحساب: ' + data.health, 'success');
      // Update row status immediately without reload if possible
      updateRowStatus(accountId, data.health);
    } else {
      showToast('خطأ: ' + data.message, 'error');
    }
  } catch (err) {
    icon.className = "fas fa-sync-alt";
    console.error(err);
    showToast('فشل الاتصال', 'error');
  }
}

function updateRowStatus(accountId, status) {
  // Find the row and update the badge
  const checkbox = document.querySelector(`.account-checkbox[value="${accountId}"]`);
  if (checkbox) {
    const row = checkbox.closest('tr');
    const statusCell = row.cells[2]; // Index 2 is status

    let badgeClass = 'badge-locked';
    let statusText = status;

    if (status === 'Active') { badgeClass = 'badge-active'; statusText = 'نشط'; }
    else if (status === 'Suspended') { badgeClass = 'badge-suspended'; statusText = 'معلق'; }
    else if (status === 'Locked') { badgeClass = 'badge-locked'; statusText = 'مقفل'; }
    else if (status === 'Invalid Cookies') { badgeClass = 'badge-locked'; statusText = 'كوكيز غير صالحة'; }

    statusCell.innerHTML = `
            <span class="badge ${badgeClass} slide-in">
                <span class="badge-dot"></span> ${statusText}
            </span>
        `;
  }
}

// --- Account Details & Editing ---

async function viewAccountDetails(id) {
  try {
    const response = await fetch('/get_account_details/' + id);
    const data = await response.json();

    if (data.status === 'success') {
      const acc = data.account;
      const content = `
                <div class="detail-section fade-in-up">
                    <div class="detail-section-title">معلومات الحساب</div>
                    <div class="detail-row">
                        <span class="detail-label">معرف الحساب</span>
                        <span class="detail-value">#${acc.id}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">اسم المستخدم</span>
                        <span class="detail-value">@${acc.username}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">الحالة</span>
                        <span class="detail-value">
                            <span class="badge ${acc.status === 'Active' ? 'badge-active' : (acc.status === 'Suspended' ? 'badge-suspended' : 'badge-locked')}">
                                <span class="badge-dot"></span> ${acc.status === 'Active' ? 'نشط' : (acc.status === 'Suspended' ? 'معلق' : (acc.status === 'Locked' ? 'مقفل' : acc.status))}
                            </span>
                        </span>
                    </div>
                </div>

                <div class="detail-section fade-in-up" style="animation-delay: 0.1s">
                    <div class="detail-section-title">إعدادات الإتصال</div>
                    <div class="detail-row">
                        <span class="detail-label">البروكسي</span>
                        <span class="detail-label">البروكسي</span>
                        <span class="detail-value">${acc.proxy || 'مباشر'}</span>
                    </div>
                    ${acc.proxy ? `<button class="copy-btn" onclick="copyToClipboard('${acc.proxy}', this)"><i class="fas fa-copy"></i> نسخ البروكسي</button>` : ''}
                </div>

                <div class="detail-section fade-in-up" style="animation-delay: 0.2s">
                    <div class="detail-section-title">إحصائيات النشاط</div>
                    <div class="detail-row">
                        <span class="detail-label">الإعجابات</span>
                        <span class="detail-value" style="color: #ff00de;">${acc.likes_count}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">إعادة التغريد</span>
                        <span class="detail-value" style="color: var(--accept);">${acc.retweets_count}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">إجمالي التفاعلات</span>
                        <span class="detail-value" style="color: var(--primary);">${acc.likes_count + acc.retweets_count}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">آخر نشاط</span>
                        <span class="detail-value">${acc.last_active}</span>
                    </div>
                </div>
                
                <div class="modal-footer" style="margin-top: 20px;">
                     <button class="btn btn-primary" onclick="openEditModal(${acc.id})" style="width:100%">
                        <i class="fas fa-edit"></i> تعديل الحساب
                     </button>
                </div>
            `;

      document.getElementById('accountDetailsContent').innerHTML = content;
      openModal('detailsModal');
    } else {
      showToast('فشل تحميل التفاصيل', 'error');
    }
  } catch (e) {
    console.error(e);
    showToast('فشل تحميل التفاصيل', 'error');
  }
}

async function openEditModal(id) {
  closeModal('detailsModal'); // Close details if open

  try {
    const response = await fetch('/get_account_details/' + id);
    const data = await response.json();

    if (data.status === 'success') {
      const acc = data.account;

      // Populate Form
      document.getElementById('edit_account_id').value = acc.id;
      document.getElementById('edit_username').value = acc.username;
      document.getElementById('edit_proxy').value = acc.proxy || '';
      document.getElementById('edit_cookies').value = acc.cookies || '';
      document.getElementById('edit_status').value = acc.status;

      openModal('editModal');
    }
  } catch (e) {
    showToast('فشل تحميل البيانات', 'error');
  }
}

async function addAccount(event) {
  event.preventDefault();
  const btn = event.target.querySelector('button[type="submit"]');
  const originalText = btn.innerHTML;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري الإضافة...';
  btn.disabled = true;

  const formData = new FormData(event.target);

  try {
    const response = await fetch('/add_account', {
      method: 'POST',
      body: formData,
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });

    // Check if response is JSON, sometimes Flask might redirect if not caught
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.indexOf("application/json") !== -1) {
      const data = await response.json();
      if (data.status === 'success') {
        showToast(data.message, 'success');
        setTimeout(() => location.reload(), 1000);
      } else {
        showToast(data.message, 'error');
        btn.innerHTML = originalText;
        btn.disabled = false;
      }
    } else {
      // Fallback or error
      const text = await response.text();
      showToast('حدث خطأ غير متوقع', 'error');
      console.error(text);
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  } catch (e) {
    showToast('حدث خطأ أثناء الإضافة', 'error');
    console.error(e);
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

async function saveAccount(event) {
  event.preventDefault();
  const btn = event.target.querySelector('button[type="submit"]');
  const originalText = btn.innerHTML;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري الحفظ...';
  btn.disabled = true;

  const id = document.getElementById('edit_account_id').value;
  const formData = new FormData(event.target);

  try {
    const response = await fetch('/update_account/' + id, {
      method: 'POST',
      body: formData,
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const data = await response.json();

    if (data.status === 'success') {
      showToast(data.message, 'success');
      setTimeout(() => location.reload(), 1000);
    } else {
      showToast(data.message, 'error');
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  } catch (e) {
    showToast('حدث خطأ أثناء الحفظ', 'error');
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

// --- Utilities ---

function copyToClipboard(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-check"></i> تم النسخ!';
    btn.classList.add('btn-success');

    setTimeout(() => {
      btn.innerHTML = originalText;
      btn.classList.remove('btn-success');
    }, 2000);
  });
}

function exportAccounts(format = 'csv') {
  const table = document.getElementById('accountsTable');
  const rows = table.querySelectorAll('tbody tr.account-row');

  if (rows.length === 0) {
    showToast('لا توجد بيانات للتصدير', 'warning');
    return;
  }

  // Collect data from table
  const data = [];
  rows.forEach(row => {
    if (row.style.display !== 'none') {
      const username = row.getAttribute('data-username');
      const status = row.getAttribute('data-status');
      const proxy = row.getAttribute('data-proxy') || '';
      const statsMinItems = row.querySelectorAll('.stat-mini-val');
      const likes = statsMinItems[0] ? parseInt(statsMinItems[0].textContent.trim()) : 0;
      const retweets = statsMinItems[1] ? parseInt(statsMinItems[1].textContent.trim()) : 0;
      const cells = row.querySelectorAll('td');
      const lastActive = cells[cells.length - 2].textContent.trim();

      data.push({
        username,
        status,
        proxy,
        likes,
        retweets,
        last_active: lastActive
      });
    }
  });

  const filename = `accounts_${new Date().toISOString().split('T')[0]}`;

  switch (format) {
    case 'json':
      exportJSON(data, filename);
      break;
    case 'csv':
      exportCSV(data, filename);
      break;
    case 'excel':
      exportExcel(data, filename);
      break;
    case 'pdf':
      exportPDF(data, filename);
      break;
    default:
      exportCSV(data, filename);
  }
}

function exportJSON(data, filename) {
  const jsonStr = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  downloadFile(blob, filename + '.json');
  showToast('تم تصدير JSON بنجاح', 'success');
}

function exportCSV(data, filename) {
  let csvContent = "Username,Status,Proxy,Likes,Retweets,Last Active\n";
  data.forEach(row => {
    csvContent += `"${row.username}","${row.status}","${row.proxy}",${row.likes},${row.retweets},"${row.last_active}"\n`;
  });
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  downloadFile(blob, filename + '.csv');
  showToast('تم تصدير CSV بنجاح', 'success');
}

function exportExcel(data, filename) {
  // Using SheetJS (XLSX)
  if (typeof XLSX === 'undefined') {
    showToast('مكتبة Excel غير متوفرة', 'error');
    return;
  }

  const ws = XLSX.utils.json_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Accounts');
  XLSX.writeFile(wb, filename + '.xlsx');
  showToast('تم تصدير Excel بنجاح', 'success');
}

function exportPDF(data, filename) {
  // Using jsPDF
  if (typeof jspdf === 'undefined' && typeof jsPDF === 'undefined') {
    showToast('مكتبة PDF غير متوفرة', 'error');
    return;
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();

  // Title
  doc.setFontSize(18);
  doc.text('Accounts Report', 14, 22);
  doc.setFontSize(11);
  doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 30);

  // Table
  const tableColumn = ['Username', 'Status', 'Proxy', 'Likes', 'Retweets'];
  const tableRows = data.map(row => [
    row.username,
    row.status,
    row.proxy || 'Direct',
    row.likes.toString(),
    row.retweets.toString()
  ]);

  doc.autoTable({
    head: [tableColumn],
    body: tableRows,
    startY: 40,
    theme: 'striped',
    headStyles: { fillColor: [0, 242, 234] }
  });

  doc.save(filename + '.pdf');
  showToast('تم تصدير PDF بنجاح', 'success');
}

function downloadFile(blob, filename) {
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// --- Import Functionality ---

async function importAccounts(event) {
  event.preventDefault();
  const fileInput = document.getElementById('importFile');
  const btn = document.getElementById('importBtn');
  const originalText = btn.innerHTML;

  if (!fileInput.files[0]) {
    showToast('الرجاء اختيار ملف', 'warning');
    return;
  }

  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري الاستيراد...';
  btn.disabled = true;

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  try {
    const response = await fetch('/api/accounts/import', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    if (data.status === 'success') {
      showToast(data.message, 'success');
      closeModal('importModal');
      setTimeout(() => location.reload(), 1500);
    } else {
      showToast(data.message, 'error');
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  } catch (err) {
    console.error(err);
    showToast('حدث خطأ أثناء الاستيراد', 'error');
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

// --- Quick Preview on Hover ---

let previewTimeout;
let activePreviewRow = null;

function initQuickPreview() {
  const rows = document.querySelectorAll('.account-row');
  const preview = document.getElementById('quickPreview');

  rows.forEach(row => {
    row.addEventListener('mouseenter', (e) => {
      activePreviewRow = row;
      previewTimeout = setTimeout(() => {
        showQuickPreview(row, e);
      }, 500); // 500ms delay before showing
    });

    row.addEventListener('mouseleave', () => {
      clearTimeout(previewTimeout);
      if (preview) preview.style.display = 'none';
      activePreviewRow = null;
    });

    row.addEventListener('mousemove', (e) => {
      if (preview && preview.style.display === 'block') {
        positionPreview(preview, e);
      }
    });
  });
}

function showQuickPreview(row, event) {
  const preview = document.getElementById('quickPreview');
  if (!preview) return;

  const username = row.getAttribute('data-username');
  const status = row.getAttribute('data-status');
  const statsMinItems = row.querySelectorAll('.stat-mini-val');
  const likes = statsMinItems[0] ? statsMinItems[0].textContent.trim() : '0';
  const retweets = statsMinItems[1] ? statsMinItems[1].textContent.trim() : '0';
  const cells = row.querySelectorAll('td');
  const lastActive = cells[cells.length - 2].textContent.trim();

  // Update preview content
  preview.querySelector('.quick-preview-name').textContent = username;
  preview.querySelector('.quick-preview-username').textContent = '@' + username.replace('@', '');
  preview.querySelector('.qp-likes').textContent = likes;
  preview.querySelector('.qp-retweets').textContent = retweets;
  preview.querySelector('.qp-last-active').textContent = lastActive || '-';

  // Show and position
  preview.style.display = 'block';
  positionPreview(preview, event);
}

function positionPreview(preview, event) {
  const x = event.clientX + 15;
  const y = event.clientY + 15;

  // Keep within viewport
  const rect = preview.getBoundingClientRect();
  const maxX = window.innerWidth - 250;
  const maxY = window.innerHeight - 150;

  preview.style.left = Math.min(x, maxX) + 'px';
  preview.style.top = Math.min(y, maxY) + 'px';
}

// Initialize quick preview when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
  initQuickPreview();
});

// Simple Toast Notification System
function showToast(message, type = 'info') {
  // Check if container exists
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type} slide-in-right`;

  let icon = 'info-circle';
  if (type === 'success') icon = 'check-circle';
  if (type === 'error') icon = 'exclamation-circle';
  if (type === 'warning') icon = 'exclamation-triangle';

  toast.innerHTML = `
        <i class="fas fa-${icon}"></i>
        <span>${message}</span>
    `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('slide-out-right');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function updateStats() {
  // Placeholder for future AJAX stat updates
}


// --- Helper Utils for Forms ---

async function pasteContent(elementId) {
  try {
    const text = await navigator.clipboard.readText();
    document.getElementById(elementId).value = text;
    showToast('تم اللصق بنجاح', 'success');
  } catch (err) {
    showToast('فشل اللصق: تأكد من صلاحيات المتصفح', 'error');
  }
}

function loadCookieFile(input) {
  const file = input.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function (e) {
    try {
      // Basic validation - check if it looks like JSON
      const text = e.target.result;
      JSON.parse(text); // Try parsing
      document.getElementById('add_cookies').value = text;
      showToast('تم تحميل الملف بنجاح', 'success');
    } catch (error) {
      // Check if it's Netscape format (advanced, maybe later) but for now just warn
      document.getElementById('add_cookies').value = e.target.result;
      showToast('تم التحميل (تنبيه: الملف قد لا يكون JSON صالح)', 'warning');
    }
  };
  reader.readAsText(file);
}

// --- Validation & Testing ---

function validateCookies(textarea) {
  const value = textarea.value.trim();
  const feedback = document.getElementById('cookiesValidation');

  if (!value) {
    textarea.style.borderColor = '';
    feedback.innerText = '';
    feedback.className = 'badge-status';
    return;
  }

  try {
    JSON.parse(value);
    textarea.style.borderColor = 'var(--accept)';
    feedback.innerText = 'JSON صالح';
    feedback.className = 'badge-status status-valid';
  } catch (e) {
    textarea.style.borderColor = 'var(--danger)';
    feedback.innerText = 'غير صالح';
    feedback.className = 'badge-status status-invalid';
  }
}

function formatJSON(elementId) {
  const textarea = document.getElementById(elementId);
  try {
    const val = JSON.parse(textarea.value);
    textarea.value = JSON.stringify(val, null, 2);
    showToast('تم تنسيق JSON بنجاح', 'success');
    validateCookies(textarea);
  } catch (e) {
    showToast('لا يمكن التنسيق: JSON غير صالح', 'error');
  }
}


function validateProxy(input) {
  const value = input.value.trim();
  const feedback = document.getElementById('proxyValidation');

  if (!value) {
    input.style.borderColor = '';
    feedback.innerText = '';
    feedback.className = 'badge-status';
    return;
  }

  // Basic regex for http/s proxy check
  const hasProtocol = value.match(/^https?:\/\//);

  if (hasProtocol) {
    input.style.borderColor = 'var(--accept)';
    feedback.innerText = 'صحيح';
    feedback.className = 'badge-status status-valid';
  } else {
    input.style.borderColor = 'orange';
    feedback.innerText = 'تنبيه: يفضل http://';
    feedback.className = 'badge-status status-invalid';
    // Warning isn't exactly invalid but let's style it
    feedback.style.background = 'rgba(255, 193, 7, 0.1)';
    feedback.style.color = '#ffc107';
    feedback.style.borderColor = 'rgba(255, 193, 7, 0.2)';
  }
}

async function testProxy() {
  const proxyInput = document.getElementById('add_proxy');
  const proxy = proxyInput.value.trim();
  const btn = document.getElementById('btn_test_proxy');
  const originalContent = btn.innerHTML;

  if (!proxy) {
    showToast('الرجاء إدخال بروكسي أولاً', 'warning');
    return;
  }

  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  btn.disabled = true;

  try {
    const response = await fetch('/test_proxy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ proxy: proxy })
    });

    const data = await response.json();

    if (data.status === 'success') {
      showToast(data.message, 'success');
      proxyInput.style.borderColor = 'var(--accept)';
    } else {
      showToast(data.message, 'error');
      proxyInput.style.borderColor = 'var(--danger)';
    }
  } catch (e) {
    showToast('فشل اختبار الاتصال', 'error');
    console.error(e);
  } finally {
    btn.innerHTML = originalContent;
    btn.disabled = false;
  }
}

async function updateAccountStats(accountId, btn) {
  const originalContent = btn.innerHTML;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  btn.disabled = true;

  try {
    const response = await fetch('/update_account_stats/' + accountId, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const data = await response.json();

    if (data.status === 'success') {
      // Update DOM elements
      const likesEl = document.getElementById(`likes-${accountId}`);
      const retweetsEl = document.getElementById(`retweets-${accountId}`);
      const lastActiveEl = document.getElementById(`last-active-${accountId}`);

      if (likesEl) likesEl.innerText = data.likes;
      if (retweetsEl) retweetsEl.innerText = data.retweets;
      if (lastActiveEl) lastActiveEl.innerText = data.last_active; // Or format it nicely

      showToast('تم تحديث الإحصائيات', 'success');
    } else {
      showToast(data.message, 'error');
    }
  } catch (e) {
    console.error(e);
    showToast('فشل التحديث', 'error');
  } finally {
    btn.innerHTML = originalContent;
    btn.disabled = false;
  }
}

// --- Sorting ---
function sortTable(n) {
  var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
  table = document.getElementById("accountsTable");
  switching = true;
  // Set the sorting direction to ascending:
  dir = "asc";

  // Basic loop to keep switching until done
  while (switching) {
    switching = false;
    rows = table.getElementsByTagName("TR");

    // Loop through all table rows (except the first, which contains table headers):
    for (i = 1; i < (rows.length - 1); i++) {
      shouldSwitch = false;

      // Get the two elements you want to compare, one from current row and one from the next:
      x = rows[i].getElementsByTagName("TD")[n];
      y = rows[i + 1].getElementsByTagName("TD")[n];

      // Check if the two rows should switch place based on direction
      var xContent = x.textContent || x.innerText;
      var yContent = y.textContent || y.innerText;

      // Try to sort numerically if possible for stats columns
      // Columns 4 (Likes/Retweets) and 5 (Date) might need special handling but simple string compare checks usually work for basic ISO dates
      // For detailed number sorting we might need more logic, but this is a good start

      if (dir == "asc") {
        if (xContent.toLowerCase() > yContent.toLowerCase()) { shouldSwitch = true; break; }
      } else if (dir == "desc") {
        if (xContent.toLowerCase() < yContent.toLowerCase()) { shouldSwitch = true; break; }
      }
    }

    if (shouldSwitch) {
      // If a switch has been marked, make the switch and mark that a switch has been done:
      rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
      switching = true;
      switchcount++;
    } else {
      // If no switching has been done AND the direction is "asc", set the direction to "desc" and run the while loop again.
      if (switchcount == 0 && dir == "asc") {
        dir = "desc";
        switching = true;
      }
    }
  }
}
