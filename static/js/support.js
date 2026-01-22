document.addEventListener("DOMContentLoaded", function () {
  setupRangeSliders();

  // Attach Event Listeners
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('input', debounce(refreshTasks, 500));
  }

  const statusFilter = document.getElementById('statusFilter');
  if (statusFilter) {
    statusFilter.addEventListener('change', refreshTasks);
  }

  const typeFilter = document.getElementById('typeFilter');
  if (typeFilter) {
    typeFilter.addEventListener('change', refreshTasks);
  }

  // Initial Load
  refreshTasks();

  // Auto Refresh every 10 seconds
  setInterval(refreshTasks, 10000);
});

function setupRangeSliders() {
  const sliders = document.querySelectorAll('input[type="range"]');
  sliders.forEach(slider => {
    slider.addEventListener('input', function () {
      const output = this.nextElementSibling;
      if (output) output.value = this.value;
    });
  });
}

function debounce(func, wait) {
  let timeout;
  return function () {
    const context = this, args = arguments;
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(context, args), wait);
  };
}

function refreshTasks() {
  const statusEl = document.getElementById('statusFilter');
  const typeEl = document.getElementById('typeFilter');
  const searchEl = document.getElementById('searchInput');

  const status = statusEl ? statusEl.value : 'all';
  const type = typeEl ? typeEl.value : 'all';
  const search = searchEl ? searchEl.value : '';

  const params = new URLSearchParams({
    status: status,
    type: type,
    search: search
  });

  fetch(`/api/tasks/list?${params.toString()}`)
    .then(res => res.json())
    .then(data => {
      renderTasks(data.tasks);
    })
    .catch(err => console.error('Error fetching tasks:', err));
}

function renderTasks(tasks) {
  const tbody = document.getElementById('tasksTableBody');
  if (!tbody) return;

  tbody.innerHTML = '';

  if (tasks.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 20px; color: #666;">لا توجد مهام مطابقة</td></tr>';
    return;
  }

  tasks.forEach(task => {
    const row = document.createElement('tr');
    row.className = `task-row ${task.status.toLowerCase().replace(' ', '-')}`;

    row.innerHTML = `
            <td style="font-family: monospace; color: var(--text-muted);">#${task.id}</td>
            <td>${getBadge(task.task_type)}</td>
            <td>
                <a href="${task.target_url}" target="_blank" class="link-preview">
                    <i class="fab fa-twitter"></i> فتح الرابط
                </a>
            </td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill ${task.progress === 100 ? 'fill-complete' : 'fill-active'}" style="width: ${task.progress}%;"></div>
                    </div>
                    <span class="progress-text">${task.completed_count} / ${task.target_count}</span>
                </div>
            </td>
            <td>
                ${getStatusBadge(task.status)}
            </td>
            <td>
                <div class="action-buttons" style="display: flex; gap: 5px;">
                    ${getControlButtons(task)}
                </div>
            </td>
        `;
    tbody.appendChild(row);
  });
}

function getBadge(type) {
  if (type === 'like') return '<span class="badge badge-like"><i class="fas fa-heart"></i> LIKE</span>';
  if (type === 'retweet') return '<span class="badge badge-retweet"><i class="fas fa-retweet"></i> RT</span>';
  if (type === 'follow') return '<span class="badge badge-follow"><i class="fas fa-user-plus"></i> FOLLOW</span>';
  return `<span class="badge badge-reply">${type.toUpperCase()}</span>`;
}

function getStatusBadge(status) {
  if (status === 'Completed') return '<span class="status-badge status-done"><i class="fas fa-check"></i> مكتمل</span>';
  if (status === 'In Progress') return '<span class="status-badge status-running"><i class="fas fa-spinner fa-spin"></i> جاري الان..</span>';
  if (status === 'Paused') return '<span class="status-badge status-paused"><i class="fas fa-pause"></i> متوقف</span>';
  if (status === 'Failed') return '<span class="status-badge status-failed"><i class="fas fa-times"></i> فشل</span>';
  return '<span class="status-badge status-pending"><i class="fas fa-clock"></i> انتظار</span>';
}

function getControlButtons(task) {
  let btns = '';

  if (task.status === 'In Progress') {
    btns += `<button onclick="taskAction(${task.id}, 'pause')" class="btn-sm btn-outline-warning" title="إيقاف مؤقت" style="background:transparent; border:1px solid #ffa502; color:#ffa502; border-radius:4px; cursor:pointer;"><i class="fas fa-pause"></i></button>`;
  } else if (task.status === 'Paused') {
    btns += `<button onclick="taskAction(${task.id}, 'resume')" class="btn-sm btn-outline-success" title="استئناف" style="background:transparent; border:1px solid #2ed573; color:#2ed573; border-radius:4px; cursor:pointer;"><i class="fas fa-play"></i></button>`;
  }

  if (task.status === 'Failed' || task.status === 'Completed' || task.status === 'Paused' || task.status === 'Pending') {
    // Retry for all non-running
  }

  if (task.status === 'Failed' || task.status === 'Completed' || task.status === 'Paused') {
    btns += `<button onclick="taskAction(${task.id}, 'retry')" class="btn-sm btn-outline-info" title="إعادة المحاولة" style="background:transparent; border:1px solid #1e90ff; color:#1e90ff; border-radius:4px; cursor:pointer; margin-left:5px;"><i class="fas fa-redo"></i></button>`;
  }

  btns += `<button onclick="taskAction(${task.id}, 'delete')" class="btn-sm btn-outline-danger" title="حذف" style="background:transparent; border:1px solid #ff4757; color:#ff4757; border-radius:4px; cursor:pointer; margin-left:5px;"><i class="fas fa-trash"></i></button>`;

  // Save Template Button
  btns += `<button onclick="openTemplateModal('${task.target_url}', '${task.task_type}', ${task.target_count})" class="btn-sm btn-outline-primary" title="حفظ كقالب" style="background:transparent; border:1px solid #a29bfe; color:#a29bfe; border-radius:4px; cursor:pointer; margin-left:5px;"><i class="fas fa-save"></i></button>`;

  return btns;
}

function taskAction(id, action) {
  let msg = `هل أنت متأكد من تنفيذ الإجراء: ${action}؟`;
  if (action === 'delete') msg = "هل أنت متأكد من حذف هذه المهمة؟";

  if (!confirm(msg)) return;

  fetch('/api/tasks/action', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: id, action: action })
  })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') refreshTasks();
    })
    .catch(err => console.error(err));
}

// Template Logic
let currentTemplateData = {};

function openTemplateModal(url, type, count) {
  currentTemplateData = { target_url: url, task_type: type, target_count: count };
  const modal = document.getElementById('templateModal');
  if (modal) modal.style.display = 'block';
}

function saveTemplateConfirm() {
  const name = document.getElementById('templateName').value;
  if (!name) return alert('يرجى إدخال اسم للقالب');

  fetch('/api/templates/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...currentTemplateData, name: name })
  })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        alert('تم حفظ القالب بنجاح');
        document.getElementById('templateModal').style.display = 'none';
      }
    });
}


// ====================================
// Load & Apply Templates
// ====================================

function toggleTemplateMenu() {
  const menu = document.getElementById('templateMenu');
  if (!menu) return;

  if (menu.style.display === 'none') {
    menu.style.display = 'block';
    loadTemplatesList();
  } else {
    menu.style.display = 'none';
  }
}

function loadTemplatesList() {
  const menu = document.getElementById('templateMenu');
  menu.innerHTML = '<div style="padding: 10px; text-align: center; color: #888; font-size: 12px;">جاري التحميل...</div>';

  fetch('/api/templates/list')
    .then(res => res.json())
    .then(data => {
      if (!data.templates || data.templates.length === 0) {
        menu.innerHTML = '<div style="padding: 10px; text-align: center; color: #888; font-size: 12px;">لا توجد قوالب محفوظة</div>';
        return;
      }

      menu.innerHTML = data.templates.map(t => `
                <div onclick='applyTemplate(${JSON.stringify(t).replace(/'/g, "&#39;")})' style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); cursor: pointer; transition: 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='transparent'">
                    <div style="font-weight: bold; color: white;">${t.name}</div>
                    <div style="font-size: 10px; color: #aaa;">${t.task_type} • ${t.target_count}</div>
                </div>
            `).join('');
    })
    .catch(err => {
      console.error(err);
      menu.innerHTML = '<div style="padding: 10px; text-align: center; color: #f00; font-size: 12px;">خطأ في التحميل</div>';
    });
}

function applyTemplate(template) {
  // Fill Form
  const urlInput = document.querySelector('input[name="target_url"]');
  if (urlInput) urlInput.value = template.target_url || '';

  // Select Radio
  const radios = document.querySelectorAll('input[name="task_type"]');
  for (const radio of radios) {
    if (radio.value === template.task_type) {
      radio.checked = true;
      radio.dispatchEvent(new Event('change')); // Trigger any listeners
      break;
    }
  }

  // Set Slider
  const slider = document.querySelector('input[name="target_count"]');
  if (slider) {
    slider.value = template.target_count;
    const output = slider.nextElementSibling;
    if (output) output.value = template.target_count;
  }

  document.getElementById('templateMenu').style.display = 'none';
}

// Close menu when clicking outside
document.addEventListener('click', function (e) {
  const menu = document.getElementById('templateMenu');
  const btn = document.querySelector('button[onclick="toggleTemplateMenu()"]');
  if (menu && menu.style.display === 'block' && !menu.contains(e.target) && (!btn || !btn.contains(e.target))) {
    menu.style.display = 'none';
  }
});

// ====================================
// Notifications System
// ====================================

// Inject Toast Container
document.addEventListener("DOMContentLoaded", function () {
  if (!document.querySelector('.toast-container')) {
    const container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
});

function showToast(title, message, type = 'info') {
  const container = document.querySelector('.toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  let icon = 'fa-info-circle';
  if (type === 'success') icon = 'fa-check-circle';
  if (type === 'error') icon = 'fa-exclamation-triangle';

  toast.innerHTML = `
        <i class="fas ${icon}" style="color: inherit;"></i>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-msg">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;

  container.appendChild(toast);

  // Auto remove
  setTimeout(() => {
    toast.style.animation = 'fadeOut 0.5s ease-out forwards';
    setTimeout(() => toast.remove(), 500);
  }, 5000);
}

// Track Task Updates for Notifications
let previousTaskStates = {};

function checkTaskUpdates(tasks) {
  tasks.forEach(task => {
    const key = task.id;
    const currentState = task.status;

    if (previousTaskStates[key]) {
      const prevState = previousTaskStates[key];

      // Pending/Running -> Completed
      if (prevState !== 'Completed' && currentState === 'Completed') {
        showToast('مهمة مكتملة', `تم الانتهاء من المهمة #${task.id} بنجاح`, 'success');
      }

      // Pending/Running -> Failed
      if (prevState !== 'Failed' && currentState === 'Failed') {
        showToast('تنبيه', `فشلت المهمة #${task.id}`, 'error');
      }
    }

    previousTaskStates[key] = currentState;
  });
}

// Hook into existing renderTasks to trigger checks
const originalRenderTasks = renderTasks;
renderTasks = function (tasks) {
  checkTaskUpdates(tasks);
  originalRenderTasks(tasks);
};
