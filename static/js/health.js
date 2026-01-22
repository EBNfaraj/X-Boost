// ====================================
// 🏥 Health Clinic JavaScript
// ====================================

// State Management
const HealthApp = {
  accounts: [],
  filteredAccounts: [],
  currentFilter: 'all',
  searchQuery: '',
  isCheckingAll: false,
  charts: {}
};

// ====================================
// Initialization
// ====================================

document.addEventListener('DOMContentLoaded', function () {
  initializeApp();
  loadCharts();
  loadRecommendations();
  attachEventListeners();
});

function initializeApp() {
  // Collect all accounts from the DOM
  const accountCards = document.querySelectorAll('.account-health-card');
  HealthApp.accounts = Array.from(accountCards).map(card => ({
    id: card.dataset.accountId,
    username: card.dataset.username,
    status: card.dataset.status,
    element: card
  }));

  HealthApp.filteredAccounts = [...HealthApp.accounts];
  updateStats();
}

// ====================================
// Event Listeners
// ====================================

function attachEventListeners() {
  // Search
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('input', handleSearch);
  }

  // Filter buttons
  const filterButtons = document.querySelectorAll('.filter-btn');
  filterButtons.forEach(btn => {
    btn.addEventListener('click', () => handleFilter(btn.dataset.filter));
  });

  // Select All checkbox
  const selectAllCheckbox = document.getElementById('selectAll');
  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener('change', handleSelectAll);
  }

  // Individual checkboxes
  const accountCheckboxes = document.querySelectorAll('.account-checkbox');
  accountCheckboxes.forEach(checkbox => {
    checkbox.addEventListener('change', updateActionButtonsState);
  });
}

// ====================================
// Search & Filter Functions
// ====================================

function handleSearch(event) {
  HealthApp.searchQuery = event.target.value.toLowerCase();
  applyFilters();
}

function handleFilter(filterType) {
  HealthApp.currentFilter = filterType;

  // Update active button
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  event.target.classList.add('active');

  applyFilters();
}

function applyFilters() {
  const accountCards = document.querySelectorAll('.account-health-card');
  let visibleCount = 0;

  accountCards.forEach(card => {
    const username = card.dataset.username.toLowerCase();
    const status = card.dataset.status.toLowerCase();

    // Check search query
    const matchesSearch = username.includes(HealthApp.searchQuery);

    // Check filter
    let matchesFilter = true;
    if (HealthApp.currentFilter !== 'all') {
      matchesFilter = status === HealthApp.currentFilter;
    }

    // Show/hide card
    if (matchesSearch && matchesFilter) {
      card.style.display = 'block';
      card.classList.add('fade-in');
      visibleCount++;
    } else {
      card.style.display = 'none';
    }
  });

  // Show empty state if no results
  const emptyState = document.getElementById('emptyState');
  const accountsGrid = document.getElementById('accountsGrid');

  if (visibleCount === 0) {
    if (emptyState) emptyState.style.display = 'block';
    if (accountsGrid) accountsGrid.style.display = 'none';
  } else {
    if (emptyState) emptyState.style.display = 'none';
    if (accountsGrid) accountsGrid.style.display = 'grid';
  }
}

// ====================================
// Selection Functions
// ====================================

function handleSelectAll(event) {
  const isChecked = event.target.checked;
  const visibleCheckboxes = document.querySelectorAll('.account-health-card:not([style*="display: none"]) .account-checkbox');

  visibleCheckboxes.forEach(checkbox => {
    checkbox.checked = isChecked;
  });

  updateActionButtonsState();
}

function getSelectedAccounts() {
  const selectedCheckboxes = document.querySelectorAll('.account-checkbox:checked');
  return Array.from(selectedCheckboxes).map(checkbox => ({
    id: checkbox.dataset.accountId,
    username: checkbox.dataset.username
  }));
}

function updateActionButtonsState() {
  const selectedCount = document.querySelectorAll('.account-checkbox:checked').length;
  const bulkActionButtons = document.querySelectorAll('.bulk-action-btn');

  bulkActionButtons.forEach(btn => {
    btn.disabled = selectedCount === 0;
  });

  // Update select all checkbox state
  const selectAllCheckbox = document.getElementById('selectAll');
  if (selectAllCheckbox) {
    const visibleCheckboxes = document.querySelectorAll('.account-health-card:not([style*="display: none"]) .account-checkbox');
    const checkedVisibleCheckboxes = Array.from(visibleCheckboxes).filter(cb => cb.checked);

    selectAllCheckbox.checked = visibleCheckboxes.length > 0 && checkedVisibleCheckboxes.length === visibleCheckboxes.length;
    selectAllCheckbox.indeterminate = checkedVisibleCheckboxes.length > 0 && checkedVisibleCheckboxes.length < visibleCheckboxes.length;
  }
}

// ====================================
// Health Check Functions
// ====================================

function checkHealth(accountId) {
  const btn = event.target.closest('button');
  const card = btn.closest('.account-health-card');
  const statusBadge = card.querySelector('.status-badge');
  const lastCheck = card.querySelector('.last-check-time');

  // Set Loading State
  const originalHTML = btn.innerHTML;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري الفحص...';
  btn.disabled = true;

  fetch(`/check_health/${accountId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        // Update status badge
        updateStatusBadge(statusBadge, data.health);

        // Update last check time
        if (lastCheck) {
          lastCheck.textContent = 'الآن';
        }

        // Update card status
        card.dataset.status = data.health.toLowerCase();

        // Update card border color
        card.className = card.className.replace(/status-\w+/, '');
        card.classList.add(`status-${data.health.toLowerCase()}`);

        // Update stats
        updateStats();

        // Update charts
        updateCharts();

        // Show success message
        showToast('تم فحص الحساب بنجاح', 'success');
      } else {
        showToast('حدث خطأ: ' + data.message, 'error');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      showToast('حدث خطأ في الاتصال', 'error');
    })
    .finally(() => {
      btn.innerHTML = originalHTML;
      btn.disabled = false;
    });
}

function checkSelectedAccounts() {
  const selected = getSelectedAccounts();

  if (selected.length === 0) {
    showToast('الرجاء تحديد حساب واحد على الأقل', 'warning');
    return;
  }

  checkMultipleAccounts(selected.map(a => a.id));
}

function checkAllAccounts() {
  const allAccountIds = HealthApp.accounts.map(a => a.id);

  if (allAccountIds.length === 0) {
    showToast('لا توجد حسابات للفحص', 'warning');
    return;
  }

  checkMultipleAccounts(allAccountIds);
}

// Check accounts in parallel
function checkMultipleAccounts(accountIds) {
  if (HealthApp.isCheckingAll) {
    showToast('يوجد فحص قيد التنفيذ بالفعل', 'warning');
    return;
  }

  HealthApp.isCheckingAll = true;

  // Show progress bar
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  const progressPercentage = document.getElementById('progressPercentage');

  if (progressContainer) {
    progressContainer.classList.add('active');
    progressBar.style.width = '10%';
    progressText.textContent = 'جاري تحضير الفحص المتوازي...';
  }

  // Use parallel API
  fetch('/api/health/check_parallel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids: accountIds })
  })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        // Animate progress to 100%
        if (progressBar) progressBar.style.width = '100%';
        if (progressPercentage) progressPercentage.textContent = '100%';

        // Update UI for each result
        data.results.forEach(res => {
          const card = document.querySelector(`[data-account-id="${res.id}"]`);
          if (card) {
            const statusBadge = card.querySelector('.status-badge');
            updateStatusBadge(statusBadge, res.status);

            const lastCheck = card.querySelector('.last-check-time');
            if (lastCheck) lastCheck.textContent = 'الآن';

            card.dataset.status = res.status.toLowerCase();
            card.className = card.className.replace(/status-\w+/, '');
            card.classList.add(`status-${res.status.toLowerCase()}`);
          }
        });

        showToast(`تم فحص ${data.results.length} حساب بنجاح`, 'success');
        updateStats();
        updateCharts();

      } else {
        showToast('حدث خطأ في الفحص', 'error');
      }
    })
    .catch(err => {
      console.error(err);
      showToast('خطأ في الاتصال', 'error');
    })
    .finally(() => {
      HealthApp.isCheckingAll = false;
      setTimeout(() => {
        if (progressContainer) progressContainer.classList.remove('active');
      }, 1500);
    });
}

function updateStatusBadge(badge, status) {
  // Remove old classes
  badge.className = 'status-badge';

  // Add new class
  const statusClass = status.toLowerCase();
  badge.classList.add(statusClass);

  // Update content
  let icon = 'fa-question-circle';
  let text = status;

  switch (statusClass) {
    case 'healthy':
      icon = 'fa-check-circle';
      break;
    case 'suspended':
    case 'locked':
    case 'invalid cookies':
      icon = 'fa-exclamation-triangle';
      break;
    default:
      icon = 'fa-question-circle';
  }

  badge.innerHTML = `<i class="fas ${icon}"></i> ${text}`;
}

// ====================================
// Stats Functions
// ====================================

function updateStats() {
  const accountCards = document.querySelectorAll('.account-health-card');

  let healthy = 0;
  let issues = 0;
  let unknown = 0;

  accountCards.forEach(card => {
    const status = card.dataset.status.toLowerCase();
    if (status === 'healthy') healthy++;
    else if (status === 'unknown') unknown++;
    else issues++;
  });

  const total = accountCards.length;
  const percentage = total > 0 ? Math.round((healthy / total) * 100) : 0;

  // Update stat cards
  const healthyEl = document.getElementById('healthyCount');
  const issuesEl = document.getElementById('issuesCount');
  const totalEl = document.getElementById('totalCount');
  const percentageEl = document.getElementById('healthPercentage');

  if (healthyEl) healthyEl.textContent = healthy;
  if (issuesEl) issuesEl.textContent = issues;
  if (totalEl) totalEl.textContent = total;
  if (percentageEl) percentageEl.textContent = percentage + '%';
}

// ====================================
// Charts Functions
// ====================================

function loadCharts() {
  createStatusPieChart();
  createTrendChart();
}

function createStatusPieChart() {
  const ctx = document.getElementById('statusChart');
  if (!ctx) return;

  const accountCards = document.querySelectorAll('.account-health-card');

  let healthy = 0;
  let issues = 0;
  let unknown = 0;

  accountCards.forEach(card => {
    const status = card.dataset.status.toLowerCase();
    if (status === 'healthy') healthy++;
    else if (status === 'unknown') unknown++;
    else issues++;
  });

  HealthApp.charts.statusChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['سليمة', 'بها مشاكل', 'غير معروفة'],
      datasets: [{
        data: [healthy, issues, unknown],
        backgroundColor: [
          '#6bcf7f',
          '#ff6b6b',
          '#8a8a9f'
        ],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#e0e0e0',
            font: {
              size: 12,
              family: 'Cairo'
            },
            padding: 15
          }
        }
      }
    }
  });
}

function createTrendChart() {
  const ctx = document.getElementById('trendChart');
  if (!ctx) return;

  // Fetch real history data from API
  fetch('/api/health/stats/history')
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        const labels = data.trend.map(d => d.date);
        const healthyData = data.trend.map(d => d.healthy);

        HealthApp.charts.trendChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels: labels,
            datasets: [{
              label: 'الحسابات السليمة',
              data: healthyData,
              borderColor: '#00d4aa',
              backgroundColor: 'rgba(0, 212, 170, 0.1)',
              tension: 0.4,
              fill: true,
              borderWidth: 2
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              y: { beginAtZero: true, grid: { color: 'rgba(45, 45, 68, 0.5)' } },
              x: { grid: { color: 'rgba(45, 45, 68, 0.5)' } }
            }
          }
        });
      }
    })
    .catch(err => console.error("Chart error:", err));
}

function updateCharts() {
  // Destroy old charts
  if (HealthApp.charts.statusChart) {
    HealthApp.charts.statusChart.destroy();
  }
  if (HealthApp.charts.trendChart) {
    HealthApp.charts.trendChart.destroy();
  }

  // Recreate charts with new data
  createStatusPieChart();
  createTrendChart();
}

// ====================================
// Export Functions
// ====================================

function exportReport() {
  const accountCards = document.querySelectorAll('.account-health-card');

  const report = {
    exportDate: new Date().toISOString(),
    totalAccounts: accountCards.length,
    accounts: []
  };

  accountCards.forEach(card => {
    report.accounts.push({
      username: card.dataset.username,
      status: card.dataset.status,
      lastCheck: card.querySelector('.last-check-time')?.textContent || 'Never'
    });
  });

  // Create downloadable file
  const dataStr = JSON.stringify(report, null, 2);
  const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);

  const exportFileDefaultName = `health-report-${new Date().toISOString().split('T')[0]}.json`;

  const linkElement = document.createElement('a');
  linkElement.setAttribute('href', dataUri);
  linkElement.setAttribute('download', exportFileDefaultName);
  linkElement.click();

  showToast('تم تصدير التقرير بنجاح', 'success');
}

// ====================================
// Toast Notifications
// ====================================

function showToast(message, type = 'info') {
  // Create toast element
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        background: ${type === 'success' ? '#6bcf7f' : type === 'error' ? '#ff6b6b' : type === 'warning' ? '#ffd93d' : '#4dabf7'};
        color: #000;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        z-index: 9999;
        font-weight: 600;
        animation: slideIn 0.3s ease;
    `;
  toast.textContent = message;

  document.body.appendChild(toast);

  // Remove after 3 seconds
  setTimeout(() => {
    toast.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ====================================
// Smart Recommendations
// ====================================

function loadRecommendations() {
  fetch('/api/health/recommendations')
    .then(res => res.json())
    .then(data => {
      const container = document.getElementById('recommendationsContainer');
      if (!container) return;

      const recs = data.recommendations;
      if (recs.length === 0) {
        container.style.display = 'none';
        return;
      }

      container.style.display = 'grid';
      container.style.gridTemplateColumns = 'repeat(auto-fit, minmax(300px, 1fr))';
      container.style.gap = '1rem';

      container.innerHTML = recs.map(rec => `
        <div class="recommendation-card ${rec.type}" style="
            background: rgba(30, 30, 46, 0.8);
            border-left: 4px solid ${getColorForType(rec.type)};
            padding: 1.5rem;
            border-radius: 12px;
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        ">
            <div class="rec-icon" style="
                background: ${getBgColorForType(rec.type)};
                color: ${getColorForType(rec.type)};
                width: 40px;
                height: 40px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.2rem;
            ">
                <i class="fas ${rec.icon}"></i>
            </div>
            <div class="rec-content" style="flex:1;">
                <h4 style="margin:0 0 0.5rem 0; color:#fff; font-size:1.1rem; font-family:'Cairo', sans-serif;">${rec.title}</h4>
                <p style="margin:0; color:#a0a0b0; font-size:0.9rem; line-height:1.5;">${rec.message}</p>
                ${rec.action ? getActionBtn(rec.action) : ''}
            </div>
        </div>
      `).join('');
    })
    .catch(err => console.error("Error loading recs:", err));
}

function getColorForType(type) {
  if (type === 'critical') return '#ff6b6b';
  if (type === 'warning') return '#ffd93d';
  if (type === 'success') return '#6bcf7f';
  return '#4dabf7'; // info
}

function getBgColorForType(type) {
  if (type === 'critical') return 'rgba(255, 107, 107, 0.1)';
  if (type === 'warning') return 'rgba(255, 217, 61, 0.1)';
  if (type === 'success') return 'rgba(107, 207, 127, 0.1)';
  return 'rgba(77, 171, 247, 0.1)';
}

function getActionBtn(action) {
  if (action === 'check_all') {
    return `<button onclick="checkAllAccounts()" style="
            margin-top: 1rem;
            background: rgba(77, 171, 247, 0.2);
            color: #4dabf7;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-family: 'Cairo', sans-serif;
            font-weight: 600;
            transition: all 0.3s;
        " onmouseover="this.style.background='rgba(77, 171, 247, 0.3)'" onmouseout="this.style.background='rgba(77, 171, 247, 0.2)'">
            <i class="fas fa-stethoscope"></i> فحص الكل الآن
        </button>`;
  }
  return '';
}
