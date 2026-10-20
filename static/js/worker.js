/**
 * GramSeva - Worker Field Portal Logic
 * Handles assigned tasks, progress updates, completion proof uploads, and notifications
 */

let workerGrievances = [];
let activeWorkerGrievanceId = null;

document.addEventListener('DOMContentLoaded', async () => {
  const user = await checkAuth();
  if (!user || user.role !== 'worker') {
    showToast('Worker access required. Use demo role switcher to log in as Worker.', 'warning');
  }

  if (user) {
    const profileBadge = document.getElementById('worker-profile-badge');
    if (profileBadge) {
      profileBadge.innerHTML = `🔧 <strong>${user.full_name}</strong> · Ward ${user.ward_number || 'N/A'}`;
    }
  }

  await loadWorkerDashboard();
  await loadWorkerLoyaltyPoints();
  await loadWorkerNotifications();
  setupWorkerProofPreview();
});

async function loadWorkerDashboard() {
  try {
    const res = await fetch('/api/grievances');
    const data = await res.json();
    if (!data.success) return;

    workerGrievances = data.grievances;

    // Calculate stats (Step 10: Assigned, In Progress, Work Completed, Rework Required)
    const countAssigned = workerGrievances.filter(g => g.status === 'ASSIGNED' || g.status === 'ACCEPTED').length;
    const countInProgress = workerGrievances.filter(g => g.status === 'IN_PROGRESS').length;
    const countCompleted = workerGrievances.filter(g => g.status === 'WORK_COMPLETED' || g.status === 'OFFICER_VERIFICATION' || g.status === 'CITIZEN_VERIFICATION' || g.status === 'VERIFIED').length;
    const countRework = workerGrievances.filter(g => g.status === 'REWORK_REQUIRED').length;
    const countTotal = workerGrievances.length;

    const elAssigned = document.getElementById('worker-stat-assigned');
    const elProgress = document.getElementById('worker-stat-progress');
    const elCompleted = document.getElementById('worker-stat-completed');
    const elRework = document.getElementById('worker-stat-rework');
    const elTotal = document.getElementById('worker-stat-total');

    if (elAssigned) elAssigned.textContent = countAssigned;
    if (elProgress) elProgress.textContent = countInProgress;
    if (elCompleted) elCompleted.textContent = countCompleted;
    if (elRework) elRework.textContent = countRework;
    if (elTotal) elTotal.textContent = countTotal;

    renderWorkerTasksTable();
  } catch (err) {
    console.error('Error loading worker dashboard:', err);
  }
}

function setWorkerStatusFilter(status) {
  const sel = document.getElementById('worker-filter-status');
  if (sel) {
    sel.value = status;
  }
  syncFilterTabs();
  renderWorkerTasksTable();
}

function syncFilterTabs() {
  const status = document.getElementById('worker-filter-status')?.value || 'ALL';
  const tabs = {
    'ALL': 'tab-all',
    'ASSIGNED': 'tab-assigned',
    'ACCEPTED': 'tab-accepted',
    'IN_PROGRESS': 'tab-in-progress',
    'WORK_COMPLETED': 'tab-completed',
    'REWORK_REQUIRED': 'tab-rework',
    'ESCALATED': 'tab-escalated'
  };

  ['tab-all', 'tab-assigned', 'tab-accepted', 'tab-in-progress', 'tab-completed', 'tab-rework', 'tab-escalated'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove('active');
  });

  const activeTabId = tabs[status];
  if (activeTabId) {
    const el = document.getElementById(activeTabId);
    if (el) el.classList.add('active');
  }
}

function renderWorkerTasksTable() {

  const tableBody = document.getElementById('worker-tasks-tbody');
  if (!tableBody) return;

  const statusFilter = document.getElementById('worker-filter-status')?.value || 'ALL';
  const priorityFilter = document.getElementById('worker-filter-priority')?.value || 'ALL';
  const searchTerm = document.getElementById('worker-search-input')?.value.toLowerCase().trim() || '';

  const filtered = workerGrievances.filter(g => {
    if (statusFilter !== 'ALL' && g.status !== statusFilter) return false;
    if (priorityFilter !== 'ALL' && g.priority !== priorityFilter) return false;
    if (searchTerm) {
      const match = g.title.toLowerCase().includes(searchTerm) ||
                    g.tracking_id.toLowerCase().includes(searchTerm) ||
                    g.location_landmark.toLowerCase().includes(searchTerm);
      if (!match) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align:center; padding:2.5rem; color:#64748B;">
          <div style="font-size:2rem; margin-bottom:0.5rem;">🔧</div>
          <div style="font-weight:600;">No Tasks Found</div>
          <p style="font-size:0.85rem; margin-top:0.25rem;">No grievances match your current filter.</p>
        </td>
      </tr>
    `;
    return;
  }

  tableBody.innerHTML = filtered.map(g => {
    const isUrgent = g.priority === 'High' && !['RESOLVED', 'CLOSED', 'REJECTED'].includes(g.status);
    const canComplete = ['IN_PROGRESS', 'REWORK_REQUIRED', 'REOPENED', 'ESCALATED'].includes(g.status);
    const canProgress = ['ACCEPTED', 'IN_PROGRESS', 'REWORK_REQUIRED', 'REOPENED', 'ESCALATED'].includes(g.status);

    let actionButtons = '';
    if (g.status === 'ASSIGNED') {
      actionButtons += `<button onclick="openWorkerAcceptModal(${g.id})" class="btn btn-sm btn-primary" style="background:#16A34A; border-color:#16A34A; font-weight:700;" title="Accept task assignment">✅ Accept</button>`;
      actionButtons += `<button onclick="openWorkerRejectModal(${g.id})" class="btn btn-sm btn-outline" style="color:#DC2626; border-color:#DC2626; font-weight:600;" title="Reject task assignment">❌ Reject</button>`;
    } else if (g.status === 'ACCEPTED') {
      actionButtons += `<button onclick="handleStartWork(${g.id}, '${g.tracking_id}')" class="btn btn-sm btn-primary" style="background:#0284C7; border-color:#0284C7; font-weight:700;" title="Start remediation work">▶️ Start Work</button>`;
    }

    if (canComplete) {
      actionButtons += `<button onclick="openWorkerCompleteModal(${g.id}, '${g.tracking_id}')" class="btn btn-sm btn-primary" title="Submit completion proof">📦 Complete</button>`;
    }
    if (canProgress) {
      actionButtons += `<button onclick="openWorkerProgressModal(${g.id}, '${g.tracking_id}', '${g.status}')" class="btn btn-sm btn-outline-primary" title="Update progress">📝 Progress</button>`;
    }
    actionButtons += `<button onclick="openGrievanceDetail('${g.tracking_id}')" class="btn btn-sm btn-outline" title="View full details">📄 Details</button>`;

    const dateDisplay = (g.assigned_at || g.created_at || '').split(' ')[0] || '--';

    return `
      <tr style="${isUrgent ? 'background: #FEF2F2;' : ''}">
        <td>
          <a href="javascript:void(0)" onclick="openGrievanceDetail('${g.tracking_id}')" class="tracking-link">${g.tracking_id}</a>
        </td>
        <td>
          <div style="font-weight:700; color:var(--text-main);">${escapeHtml(g.title)}</div>
          <div style="font-size:0.75rem; color:#64748B;">Ward ${g.ward_number} • ${escapeHtml(g.location_landmark)}</div>
        </td>
        <td>
          <span class="category-pill">${getCategoryIcon(g.category)} ${g.category.split(' ')[0]}</span>
        </td>
        <td>${getPriorityBadge(g.priority)}</td>
        <td>${getStatusBadge(g.status)}</td>
        <td style="font-size:0.8rem; color:#64748B;">${dateDisplay}</td>
        <td>
          <div style="display:flex; gap:0.35rem; align-items:center; flex-wrap:wrap;">
            ${actionButtons}
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// ==========================================
// WORKER ASSIGNMENT ACCEPT / REJECT HANDLERS
// ==========================================
function openWorkerAcceptModal(id) {
  activeWorkerGrievanceId = id;
  const g = workerGrievances.find(item => item.id === id);
  if (!g) return;

  const elTracking = document.getElementById('worker-accept-tracking-id');
  if (elTracking) elTracking.textContent = g.tracking_id;

  const elTitle = document.getElementById('worker-accept-title');
  if (elTitle) elTitle.textContent = `${g.title} (${g.location_landmark}, Ward ${g.ward_number})`;

  openModal('modal-worker-accept');
}

async function handleWorkerAcceptSubmit(event) {
  event.preventDefault();
  if (!activeWorkerGrievanceId) return;

  const btn = document.getElementById('btn-confirm-accept');
  if (btn) { btn.disabled = true; btn.textContent = 'Accepting...'; }

  try {
    const res = await fetch(`/api/worker/grievances/${activeWorkerGrievanceId}/accept`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message || 'Task successfully accepted! Assigned to active tasks queue.', 'success');
      closeModal('modal-worker-accept');
      await loadWorkerDashboard();
      await loadWorkerLoyaltyPoints();
    } else {
      showToast(data.error || 'Failed to accept task', 'error');
    }
  } catch (err) {
    showToast('Network error while accepting task: ' + err.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '✅ Confirm & Accept Work'; }
  }
}

function openWorkerRejectModal(id) {
  activeWorkerGrievanceId = id;
  const g = workerGrievances.find(item => item.id === id);
  if (!g) return;

  const elTracking = document.getElementById('worker-reject-tracking-id');
  if (elTracking) elTracking.textContent = g.tracking_id;

  const elTitle = document.getElementById('worker-reject-title');
  if (elTitle) elTitle.textContent = `${g.title} (${g.location_landmark}, Ward ${g.ward_number})`;

  const elReason = document.getElementById('worker-reject-reason');
  if (elReason) elReason.value = '';

  openModal('modal-worker-reject');
}

async function handleWorkerRejectSubmit(event) {
  event.preventDefault();
  if (!activeWorkerGrievanceId) return;

  const reasonEl = document.getElementById('worker-reject-reason');
  const reason = reasonEl ? reasonEl.value.trim() : '';
  if (!reason) {
    showToast('A mandatory rejection reason is required.', 'warning');
    if (reasonEl) reasonEl.focus();
    return;
  }

  const btn = document.getElementById('btn-confirm-reject');
  if (btn) { btn.disabled = true; btn.textContent = 'Rejecting & Deducting Penalty...'; }

  try {
    const res = await fetch(`/api/worker/grievances/${activeWorkerGrievanceId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: reason })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message || 'Assignment rejected and released back to administration. 5 Loyalty Points deducted.', 'warning');
      closeModal('modal-worker-reject');
      if (reasonEl) reasonEl.value = '';
      await loadWorkerDashboard();
      await loadWorkerLoyaltyPoints();
    } else {
      showToast(data.error || 'Failed to reject task', 'error');
    }
  } catch (err) {
    showToast('Network error while rejecting task: ' + err.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '❌ Confirm Rejection & Deduct Penalty'; }
  }
}

async function handleStartWork(id, trackingId) {
  if (!confirm(`Start remediation work for ${trackingId}? Grievance status will change to IN PROGRESS.`)) {
    return;
  }

  try {
    const res = await fetch(`/api/grievances/${id}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: 'IN_PROGRESS',
        remarks: 'Worker commenced on-site remediation operations.'
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message || `Work started on ${trackingId}`, 'success');
      await loadWorkerDashboard();
    } else {
      showToast(data.error || 'Could not update status to In Progress', 'error');
    }
  } catch (err) {
    showToast('Failed to start work: ' + err.message, 'error');
  }
}

// ==========================================
// WORKER PROGRESS UPDATE
// ==========================================
function openWorkerProgressModal(id, trackingId, currentStatus) {
  activeWorkerGrievanceId = id;
  document.getElementById('worker-progress-tracking-id').textContent = trackingId;
  const statusSelect = document.getElementById('worker-progress-status');
  if (statusSelect) {
    statusSelect.value = currentStatus === 'REWORK_REQUIRED' ? 'IN_PROGRESS' : currentStatus;
  }
  openModal('modal-worker-progress');
}

async function handleWorkerProgressSubmit(event) {
  event.preventDefault();
  if (!activeWorkerGrievanceId) return;

  const newStatus = document.getElementById('worker-progress-status').value;
  const remarks = document.getElementById('worker-progress-remarks').value.trim();

  if (!remarks) {
    showToast('Progress remarks are mandatory', 'warning');
    return;
  }

  try {
    const res = await fetch(`/api/grievances/${activeWorkerGrievanceId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: newStatus,
        remarks: remarks
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      closeModal('modal-worker-progress');
      document.getElementById('worker-progress-remarks').value = '';
      await loadWorkerDashboard();
    } else {
      showToast(data.error, 'error');
    }
  } catch (err) {
    showToast('Failed to update progress: ' + err.message, 'error');
  }
}

// ==========================================
// WORKER COMPLETE WORK & UPLOAD PROOF
// ==========================================
function openWorkerCompleteModal(id, trackingId) {
  activeWorkerGrievanceId = id;
  document.getElementById('worker-complete-tracking-id').textContent = trackingId;
  // Reset form
  const form = document.getElementById('form-worker-complete');
  if (form) form.reset();
  document.getElementById('worker-proof-preview').innerHTML = '';

  const tsInput = document.getElementById('worker-completion-timestamp');
  if (tsInput) {
    const now = new Date();
    const localIso = new Date(now.getTime() - (now.getTimezoneOffset() * 60000)).toISOString().slice(0, 16);
    tsInput.value = localIso;
  }

  // Display Rework / Reopen / Escalation Reason if applicable
  const reworkBox = document.getElementById('worker-complete-rework-box');
  const reworkTitle = document.getElementById('worker-complete-rework-title');
  const reworkReason = document.getElementById('worker-complete-rework-reason');
  if (reworkBox && reworkTitle && reworkReason) {
    const g = workerGrievances.find(item => item.id === id);
    if (g && ['REWORK_REQUIRED', 'REOPENED', 'ESCALATED'].includes(g.status)) {
      reworkBox.style.display = 'block';
      if (g.status === 'REWORK_REQUIRED') {
        reworkTitle.textContent = '🔁 Rework Required: Supervising officer or citizen reported incomplete resolution';
      } else if (g.status === 'REOPENED') {
        reworkTitle.textContent = '⚠️ Reopened Grievance: Citizen verified that problem still exists';
      } else {
        reworkTitle.textContent = '🚨 ESCALATED: Priority rework required under senior Panchayat oversight';
      }

      // Fetch latest remarks from grievance detail
      fetch(`/api/grievances/${id}`)
        .then(res => res.json())
        .then(data => {
          if (data.success && data.grievance) {
            const fullG = data.grievance;
            let reasonText = '';
            if (fullG.officer_verifications && fullG.officer_verifications.length > 0) {
              const latestOv = fullG.officer_verifications[0];
              reasonText = `Officer ${latestOv.officer_name || ''}: "${latestOv.remarks}"`;
            }
            if (fullG.citizen_verifications && fullG.citizen_verifications.length > 0) {
              const latestCv = fullG.citizen_verifications[0];
              if (latestCv.response !== 'YES') {
                reasonText += (reasonText ? ' | ' : '') + `Citizen (${latestCv.response}): "${latestCv.remarks || 'Problem unresolved'}"`;
              }
            }
            reworkReason.textContent = reasonText || 'Please inspect the site, rectify remaining defects, and submit updated proof.';
          }
        })
        .catch(() => {
          reworkReason.textContent = 'Please re-inspect the issue, rectify remaining defects, and upload updated proof.';
        });
    } else {
      reworkBox.style.display = 'none';
    }
  }

  openModal('modal-worker-complete');
}

async function handleWorkerCompleteSubmit(event) {
  event.preventDefault();
  if (!activeWorkerGrievanceId) return;

  const form = event.target;
  const submitBtn = form.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Uploading...';

  try {
    const formData = new FormData(form);

    const res = await fetch(`/api/grievances/${activeWorkerGrievanceId}/complete-work`, {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      closeModal('modal-worker-complete');
      await loadWorkerDashboard();
    } else {
      showToast(data.error, 'error');
    }
  } catch (err) {
    showToast('Failed to submit completion proof: ' + err.message, 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = '📦 Submit Completion Proof';
  }
}

function setupWorkerProofPreview() {
  const fileInput = document.getElementById('worker-proof-file');
  const previewArea = document.getElementById('worker-proof-preview');
  if (!fileInput || !previewArea) return;

  fileInput.addEventListener('change', (e) => {
    previewArea.innerHTML = '';
    const file = e.target.files[0];
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (re) => {
        previewArea.innerHTML = `
          <div style="margin-top:0.5rem; display:inline-block; position:relative; border-radius:8px; overflow:hidden; border:1px solid #CBD5E1;">
            <img src="${re.target.result}" style="max-height:120px; display:block; object-fit:cover;" />
            <div style="background:rgba(0,0,0,0.6); color:#fff; font-size:0.7rem; padding:2px 6px; text-align:center;">Resolution Proof</div>
          </div>
        `;
      };
      reader.readAsDataURL(file);
    } else if (file) {
      previewArea.innerHTML = `<div style="font-size:0.82rem; color:#475569; margin-top:0.4rem;">📄 ${file.name} selected</div>`;
    }
  });
}

// ==========================================
// WORKER NOTIFICATIONS
// ==========================================
async function loadWorkerNotifications() {
  const listEl = document.getElementById('worker-notifications-list');
  if (!listEl) return;

  try {
    const res = await fetch('/api/notifications');
    const data = await res.json();
    if (!data.success) return;

    const notifs = data.notifications;
    if (notifs.length === 0) {
      listEl.innerHTML = `<div style="color:#64748B; padding:1rem; font-size:0.85rem;">No notifications yet.</div>`;
      return;
    }

    listEl.innerHTML = notifs.map(n => `
      <div style="padding:0.75rem 0; border-bottom:1px solid #E2E8F0; ${n.is_read ? 'opacity:0.65;' : ''}">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <div style="font-weight:${n.is_read ? '400' : '700'}; font-size:0.88rem; color:var(--text-main);">${escapeHtml(n.title)}</div>
            <div style="font-size:0.82rem; color:#475569; margin-top:0.2rem;">${escapeHtml(n.message)}</div>
          </div>
          <div style="font-size:0.72rem; color:#94A3B8; white-space:nowrap; margin-left:0.5rem;">${n.created_at.split(' ')[0]}</div>
        </div>
        ${!n.is_read ? `<button onclick="markWorkerNotificationRead(${n.id})" style="font-size:0.72rem; color:var(--civic-green); background:none; border:none; cursor:pointer; padding:0.2rem 0; font-weight:600;">Mark Read</button>` : ''}
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading notifications:', err);
  }
}

async function markWorkerNotificationRead(nid) {
  try {
    await fetch(`/api/notifications/${nid}/read`, { method: 'POST' });
    await loadWorkerNotifications();
  } catch (err) {
    showToast('Failed to mark notification as read', 'error');
  }
}

async function markAllWorkerNotificationsRead() {
  try {
    await fetch('/api/notifications/read-all', { method: 'POST' });
    showToast('All notifications marked as read', 'success');
    await loadWorkerNotifications();
  } catch (err) {
    showToast('Failed to mark all as read', 'error');
  }
}

// ==========================================
// Worker Loyalty Points & Recognition Ledger
// ==========================================

async function loadWorkerLoyaltyPoints() {
  try {
    const res = await fetch('/api/worker/loyalty-points');
    const data = await res.json();
    if (!data.success) {
      console.warn('Could not load worker loyalty points:', data.error);
      return;
    }

    const worker = data.worker || {};
    const points = worker.loyalty_points !== undefined ? worker.loyalty_points : '--';
    const transactions = data.transactions || [];

    // Update stat and header values
    const elStatPoints = document.getElementById('worker-stat-points');
    if (elStatPoints) elStatPoints.textContent = points;

    const elHeaderPoints = document.getElementById('worker-header-points');
    if (elHeaderPoints) elHeaderPoints.textContent = points;

    const elDisplayPoints = document.getElementById('worker-points-current-display');
    if (elDisplayPoints) elDisplayPoints.textContent = points;

    const elStatusBadge = document.getElementById('worker-points-status-badge');
    if (elStatusBadge) {
      elStatusBadge.textContent = `${points} Verified Points`;
      if (points >= 100) {
        elStatusBadge.style.background = '#DCFCE7';
        elStatusBadge.style.color = '#15803D';
      } else if (points >= 50) {
        elStatusBadge.style.background = '#FEF3C7';
        elStatusBadge.style.color = '#B45309';
      } else {
        elStatusBadge.style.background = '#FEE2E2';
        elStatusBadge.style.color = '#B91C1C';
      }
    }

    renderWorkerPointsTransactionsTable(transactions);
  } catch (err) {
    console.error('Error fetching worker loyalty points:', err);
  }
}

function renderWorkerPointsTransactionsTable(transactions) {
  const tbody = document.getElementById('worker-points-history-tbody');
  if (!tbody) return;

  if (!transactions || transactions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:1.75rem; color:#64748B;">No points transactions recorded yet.</td></tr>';
    return;
  }

  tbody.innerHTML = transactions.map(tx => {
    const isPositive = tx.points_changed > 0;
    const changeBadge = isPositive 
      ? `<span class="badge" style="background:#DCFCE7; color:#15803D; font-weight:700; font-size:0.85rem;">+${tx.points_changed} pts</span>`
      : `<span class="badge" style="background:#FEE2E2; color:#B91C1C; font-weight:700; font-size:0.85rem;">${tx.points_changed} pts</span>`;

    const formattedDate = tx.created_at ? tx.created_at.replace('T', ' ').substring(0, 19) : 'N/A';

    return `
      <tr>
        <td style="font-size:0.82rem; color:#475569; white-space:nowrap;">
          🕒 ${formattedDate}
        </td>
        <td>
          <div style="font-weight:600; color:var(--text-main);">${escapeHtml(tx.reason)}</div>
          <div style="font-size:0.75rem; color:#64748B;">Audit Ref: <code>#TX-${tx.id}</code></div>
        </td>
        <td style="text-align:center;">
          ${changeBadge}
        </td>
        <td style="text-align:right; font-family:monospace; font-size:0.9rem;">
          <span style="color:#64748B;">${tx.previous_balance}</span> &rarr; 
          <strong style="color:var(--civic-dark);">${tx.new_balance}</strong>
        </td>
        <td style="font-size:0.82rem; color:#334155;">
          🛡️ ${escapeHtml(tx.actor_source || 'System')}
        </td>
      </tr>
    `;
  }).join('');
}
