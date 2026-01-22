/**
 * Dashboard JavaScript - X-Boost Pro
 * Interactive Charts & Dynamic Updates
 */

// ========== Configuration ==========
const CONFIG = {
  refreshInterval: 30000, // 30 seconds
  apiEndpoints: {
    stats: '/api/dashboard/stats',
    charts: '/api/dashboard/charts',
    alerts: '/api/dashboard/alerts',
    liveStatus: '/api/dashboard/live-status',
    comparison: '/api/dashboard/comparison'
  }
};

// ========== Global Variables ==========
let accountsChart = null;
let activityChart = null;
let tasksChart = null;
let refreshTimer = null;

// ========== Daily Tips ==========
const dailyTips = [
  {
    title: "نصيحة اليوم: التوزيع الذكي",
    desc: "قم بتوزيع المهام على فترات زمنية متباعدة لتجنب الكشف. يُفضل الانتظار 30-60 ثانية بين كل عملية."
  },
  {
    title: "أفضل الممارسات: صحة الحسابات",
    desc: "تأكد من فحص صحة الحسابات بانتظام. الحسابات الصحية تعطي نتائج أفضل وتدوم لفترة أطول."
  },
  {
    title: "نصيحة: البروكسيات",
    desc: "استخدم بروكسيات مختلفة لكل حساب لزيادة الأمان وتقليل احتمالية الحظر."
  },
  {
    title: "تذكير: النسخ الاحتياطي",
    desc: "قم بتصدير بيانات الحسابات بشكل دوري للحفاظ عليها من الضياع."
  },
  {
    title: "أفضل الممارسات: التنويع",
    desc: "نوّع في أنواع التفاعلات (إعجابات، إعادة تغريد، تعليقات) للحصول على نتائج طبيعية."
  }
];

// ========== Initialization ==========
document.addEventListener('DOMContentLoaded', function () {
  console.log('🚀 Dashboard initialized');

  // Initialize Charts
  initializeCharts();

  // Load initial data
  loadDashboardData();

  // Set daily tip
  setDailyTip();

  // Start auto-refresh
  startAutoRefresh();
});

// ========== Charts Initialization ==========
function initializeCharts() {
  // Chart.js global defaults
  Chart.defaults.font.family = "'Cairo', sans-serif";
  Chart.defaults.color = '#8b8b9b';

  // Accounts Distribution Chart (Doughnut)
  const accountsCtx = document.getElementById('accountsChart');
  if (accountsCtx) {
    accountsChart = new Chart(accountsCtx, {
      type: 'doughnut',
      data: {
        labels: ['نشط', 'معلق', 'مقفل'],
        datasets: [{
          data: [0, 0, 0],
          backgroundColor: [
            'rgba(0, 255, 157, 0.8)',
            'rgba(255, 149, 0, 0.8)',
            'rgba(255, 42, 42, 0.8)'
          ],
          borderColor: [
            'rgba(0, 255, 157, 1)',
            'rgba(255, 149, 0, 1)',
            'rgba(255, 42, 42, 1)'
          ],
          borderWidth: 2,
          hoverOffset: 10
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
        plugins: {
          legend: {
            position: 'bottom',
            rtl: true,
            labels: {
              padding: 20,
              usePointStyle: true,
              pointStyle: 'circle'
            }
          },
          tooltip: {
            rtl: true,
            textDirection: 'rtl',
            callbacks: {
              label: function (context) {
                return context.label + ': ' + context.parsed + ' حساب';
              }
            }
          }
        },
        animation: {
          animateRotate: true,
          animateScale: true
        }
      }
    });
  }

  // Daily Activity Chart (Line)
  const activityCtx = document.getElementById('activityChart');
  if (activityCtx) {
    const gradient = activityCtx.getContext('2d').createLinearGradient(0, 0, 0, 250);
    gradient.addColorStop(0, 'rgba(0, 242, 234, 0.3)');
    gradient.addColorStop(1, 'rgba(0, 242, 234, 0)');

    activityChart = new Chart(activityCtx, {
      type: 'line',
      data: {
        labels: getLast7Days(),
        datasets: [{
          label: 'العمليات',
          data: [0, 0, 0, 0, 0, 0, 0],
          fill: true,
          backgroundColor: gradient,
          borderColor: 'rgba(0, 242, 234, 1)',
          borderWidth: 3,
          tension: 0.4,
          pointBackgroundColor: 'rgba(0, 242, 234, 1)',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(255, 255, 255, 0.05)',
              drawBorder: false
            },
            ticks: {
              padding: 10
            }
          },
          x: {
            grid: {
              display: false
            },
            ticks: {
              padding: 10
            }
          }
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            rtl: true,
            textDirection: 'rtl',
            backgroundColor: 'rgba(19, 19, 31, 0.9)',
            padding: 12,
            cornerRadius: 8,
            callbacks: {
              label: function (context) {
                return context.parsed.y + ' عملية';
              }
            }
          }
        },
        interaction: {
          intersect: false,
          mode: 'index'
        }
      }
    });
  }

  // Monthly Tasks Chart (Bar)
  const tasksCtx = document.getElementById('tasksChart');
  if (tasksCtx) {
    tasksChart = new Chart(tasksCtx, {
      type: 'bar',
      data: {
        labels: ['مكتملة', 'قيد التنفيذ', 'معلقة', 'فاشلة'],
        datasets: [{
          label: 'المهام',
          data: [0, 0, 0, 0],
          backgroundColor: [
            'rgba(0, 255, 157, 0.8)',
            'rgba(0, 242, 234, 0.8)',
            'rgba(255, 149, 0, 0.8)',
            'rgba(255, 42, 42, 0.8)'
          ],
          borderColor: [
            'rgba(0, 255, 157, 1)',
            'rgba(0, 242, 234, 1)',
            'rgba(255, 149, 0, 1)',
            'rgba(255, 42, 42, 1)'
          ],
          borderWidth: 2,
          borderRadius: 8,
          borderSkipped: false
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(255, 255, 255, 0.05)',
              drawBorder: false
            },
            ticks: {
              padding: 10,
              stepSize: 1
            }
          },
          x: {
            grid: {
              display: false
            },
            ticks: {
              padding: 10
            }
          }
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            rtl: true,
            textDirection: 'rtl',
            backgroundColor: 'rgba(19, 19, 31, 0.9)',
            padding: 12,
            cornerRadius: 8,
            callbacks: {
              label: function (context) {
                return context.parsed.y + ' مهمة';
              }
            }
          }
        }
      }
    });
  }
}

// ========== Data Loading ==========
async function loadDashboardData() {
  showRefreshing(true);

  try {
    // Load all data in parallel
    const [stats, charts, alerts, liveStatus, comparison] = await Promise.all([
      fetchData(CONFIG.apiEndpoints.stats),
      fetchData(CONFIG.apiEndpoints.charts),
      fetchData(CONFIG.apiEndpoints.alerts),
      fetchData(CONFIG.apiEndpoints.liveStatus),
      fetchData(CONFIG.apiEndpoints.comparison)
    ]);

    // Update UI components
    if (stats) updateKPIs(stats);
    if (charts) updateCharts(charts);
    if (alerts) updateAlerts(alerts);
    if (liveStatus) updateLiveStatus(liveStatus);
    if (comparison) updateComparison(comparison);

  } catch (error) {
    console.error('Error loading dashboard data:', error);
  }

  showRefreshing(false);
}

async function fetchData(endpoint) {
  try {
    const response = await fetch(endpoint);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.warn(`Failed to fetch ${endpoint}:`, error);
    return null;
  }
}

// ========== Update Functions ==========
function updateKPIs(stats) {
  // Active Accounts
  animateValue('kpi-accounts', stats.active_accounts || 0);
  updateProgress('progress-accounts', stats.accounts_percentage || 0);
  updateTrend('trend-accounts', stats.accounts_trend || 0);

  // Total Actions
  animateValue('kpi-actions', stats.total_actions || 0);
  updateProgress('progress-actions', stats.actions_percentage || 0);
  updateTrend('trend-actions', stats.actions_trend || 0);

  // Pending Tasks
  animateValue('kpi-pending', stats.pending_tasks || 0);
  updateProgress('progress-pending', stats.pending_percentage || 0);

  // Success Rate
  animateValue('kpi-success', stats.success_rate || 0, '%');
  updateProgress('progress-success', stats.success_rate || 0);
  updateTrend('trend-success', stats.success_trend || 0);
}

function updateCharts(chartData) {
  // Update Accounts Chart
  if (accountsChart && chartData.accounts) {
    accountsChart.data.datasets[0].data = [
      chartData.accounts.active || 0,
      chartData.accounts.suspended || 0,
      chartData.accounts.locked || 0
    ];
    accountsChart.update('none');
  }

  // Update Activity Chart
  if (activityChart && chartData.daily_activity) {
    activityChart.data.datasets[0].data = chartData.daily_activity;
    activityChart.update('none');
  }

  // Update Tasks Chart
  if (tasksChart && chartData.tasks) {
    tasksChart.data.datasets[0].data = [
      chartData.tasks.completed || 0,
      chartData.tasks.in_progress || 0,
      chartData.tasks.pending || 0,
      chartData.tasks.failed || 0
    ];
    tasksChart.update('none');
  }
}

function updateAlerts(alerts) {
  const container = document.getElementById('alerts-container');
  if (!container) return;

  if (!alerts || alerts.length === 0) {
    container.innerHTML = `
            <div class="no-alerts">
                <i class="fas fa-check-circle"></i>
                <p>لا توجد تنبيهات حالياً</p>
            </div>
        `;
    return;
  }

  container.innerHTML = alerts.map(alert => `
        <div class="alert-item ${alert.type}">
            <div class="alert-icon">
                <i class="fas ${getAlertIcon(alert.type)}"></i>
            </div>
            <div class="alert-content">
                <div class="alert-title">${alert.title}</div>
                <div class="alert-desc">${alert.message}</div>
            </div>
            <div class="alert-time">${alert.time || ''}</div>
        </div>
    `).join('');
}

function updateLiveStatus(status) {
  animateValue('live-tasks', status.running_tasks || 0);
  animateValue('live-accounts', status.active_accounts || 0);

  const lastActivity = document.getElementById('live-activity');
  if (lastActivity) {
    lastActivity.textContent = status.last_activity || 'غير متوفر';
  }
}

function updateComparison(comparison) {
  // Weekly comparison
  updateComparisonItem('comp-week-current', comparison.week?.current || 0);
  updateComparisonItem('comp-week-previous', comparison.week?.previous || 0, 'الأسبوع الماضي: ');
  updateComparisonBadge('comp-week-badge', comparison.week?.change || 0);

  // Monthly comparison
  updateComparisonItem('comp-month-current', comparison.month?.current || 0);
  updateComparisonItem('comp-month-previous', comparison.month?.previous || 0, 'الشهر الماضي: ');
  updateComparisonBadge('comp-month-badge', comparison.month?.change || 0);
}

// ========== Helper Functions ==========
function animateValue(elementId, value, suffix = '') {
  const element = document.getElementById(elementId);
  if (!element) return;

  const start = parseInt(element.textContent) || 0;
  const end = parseInt(value);
  const duration = 1000;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const easeProgress = 1 - Math.pow(1 - progress, 3); // Ease out cubic
    const current = Math.round(start + (end - start) * easeProgress);
    element.textContent = current + suffix;

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}

function updateProgress(elementId, percentage) {
  const element = document.getElementById(elementId);
  if (element) {
    element.style.width = Math.min(percentage, 100) + '%';
  }
}

function updateTrend(elementId, change) {
  const element = document.getElementById(elementId);
  if (!element) return;

  if (change > 0) {
    element.className = 'trend up';
    element.innerHTML = `<i class="fas fa-arrow-up"></i> +${change}%`;
  } else if (change < 0) {
    element.className = 'trend down';
    element.innerHTML = `<i class="fas fa-arrow-down"></i> ${change}%`;
  } else {
    element.className = 'trend';
    element.innerHTML = '';
  }
}

function updateComparisonItem(elementId, value, prefix = '') {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = prefix + value;
  }
}

function updateComparisonBadge(elementId, change) {
  const element = document.getElementById(elementId);
  if (!element) return;

  if (change > 0) {
    element.className = 'comparison-badge up';
    element.innerHTML = `<i class="fas fa-arrow-up"></i> +${change}%`;
  } else if (change < 0) {
    element.className = 'comparison-badge down';
    element.innerHTML = `<i class="fas fa-arrow-down"></i> ${change}%`;
  } else {
    element.className = 'comparison-badge';
    element.textContent = '0%';
  }
}

function getAlertIcon(type) {
  switch (type) {
    case 'danger': return 'fa-exclamation-circle';
    case 'warning': return 'fa-exclamation-triangle';
    case 'info': return 'fa-info-circle';
    default: return 'fa-bell';
  }
}

function getLast7Days() {
  const days = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
  const result = [];
  const today = new Date();

  for (let i = 6; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    result.push(days[date.getDay()]);
  }

  return result;
}

function setDailyTip() {
  const tipContainer = document.getElementById('daily-tip');
  if (!tipContainer) return;

  // Select tip based on day of month
  const dayOfMonth = new Date().getDate();
  const tipIndex = dayOfMonth % dailyTips.length;
  const tip = dailyTips[tipIndex];

  const titleEl = tipContainer.querySelector('.tip-title');
  const descEl = tipContainer.querySelector('.tip-desc');

  if (titleEl) titleEl.textContent = tip.title;
  if (descEl) descEl.textContent = tip.desc;
}

// ========== Auto Refresh ==========
function startAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }

  refreshTimer = setInterval(() => {
    console.log('🔄 Auto-refreshing dashboard...');
    loadDashboardData();
  }, CONFIG.refreshInterval);

  // Update countdown display
  updateRefreshCountdown();
}

function updateRefreshCountdown() {
  let seconds = CONFIG.refreshInterval / 1000;
  const indicator = document.getElementById('refresh-indicator');

  setInterval(() => {
    seconds--;
    if (seconds <= 0) seconds = CONFIG.refreshInterval / 1000;

    if (indicator) {
      const text = indicator.querySelector('.refresh-text');
      if (text) {
        text.textContent = `تحديث بعد ${seconds} ثانية`;
      }
    }
  }, 1000);
}

function showRefreshing(isRefreshing) {
  const indicator = document.getElementById('refresh-indicator');
  if (indicator) {
    if (isRefreshing) {
      indicator.classList.add('refreshing');
      const text = indicator.querySelector('.refresh-text');
      if (text) text.textContent = 'جاري التحديث...';
    } else {
      indicator.classList.remove('refreshing');
    }
  }
}

// ========== Manual Refresh ==========
function refreshDashboard() {
  loadDashboardData();
}

// ========== Cleanup ==========
window.addEventListener('beforeunload', function () {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
});
