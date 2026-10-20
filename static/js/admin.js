/**
 * GramSeva - Panchayat Admin & Official Operations Logic
 * Verification, Assignment, Status Lifecycle, Notices, Officer Management
 */

let allAdminGrievances = [];
let allDepartments = [];
let allOfficers = [];
let allWorkers = [];
let activeGrievanceForAction = null;

document.addEventListener('DOMContentLoaded', async () => {
  const user = await checkAuth();
  if (!user || (user.role !== 'admin' && user.role !== 'officer')) {
    showToast('Admin access required. Use demo role switcher to log in as Admin or Officer.', 'warning');
  }
  await loadDepartmentsAndOfficers();
  await loadAdminDashboard();
  loadAnnouncementsManager();
});

async function loadDepartmentsAndOfficers() {
  try {
    const [deptRes, offRes, wrkRes] = await Promise.all([
      fetch('/api/departments'),
      fetch('/api/officers'),
      fetch('/api/workers')
    ]);
    const dData = await deptRes.json();
    const oData = await offRes.json();
    const wData = await wrkRes.json();
    if (dData.success) allDepartments = dData.departments;
    if (oData.success) allOfficers = oData.officers;
    if (wData.success) allWorkers = wData.workers;

    populateDepartmentDropdowns();
    renderOfficerRoster();
  } catch (err) {
    console.error('Error loading depts/officers:', err);
  }
}


function populateDepartmentDropdowns() {
  const deptSelect = document.getElementById('assign-department-select');
  const catFilter = document.getElementById('admin-filter-category');

  if (deptSelect) {
    deptSelect.innerHTML = `<option value="">-- Choose Department --</option>` +
      allDepartments.map(d => `<option value="${d.id}">${d.name} (${d.code})</option>`).join('');
  }

  if (catFilter) {
    catFilter.innerHTML = `<option value="ALL">All Categories</option>` +
      allDepartments.map(d => `<option value="${d.name}">${d.name}</option>`).join('');
  }
}

async function loadAdminDashboard() {
  try {
    const res = await fetch('/api/grievances?scope=all');
    const data = await res.json();
    if (!data.success) return;

    allAdminGrievances = data.grievances;

    // Calculate Summary Stats
    const total = allAdminGrievances.length;
    const pending = allAdminGrievances.filter(g => g.status === 'SUBMITTED' || g.status === 'UNDER_REVIEW').length;
    const progress = allAdminGrievances.filter(g => g.status === 'ASSIGNED' || g.status === 'IN_PROGRESS').length;
    const resolved = allAdminGrievances.filter(g => g.status === 'RESOLVED' || g.status === 'CLOSED').length;
    const highAlerts = allAdminGrievances.filter(g => g.priority === 'High' && g.status !== 'RESOLVED' && g.status !== 'CLOSED' && g.status !== 'REJECTED').length;
    const awaitingList = allAdminGrievances.filter(g => g.status === 'WORK_COMPLETED' || g.status === 'OFFICER_VERIFICATION');

    const elTotal = document.getElementById('admin-stat-total');
    const elPending = document.getElementById('admin-stat-pending');
    const elProgress = document.getElementById('admin-stat-progress');
    const elResolved = document.getElementById('admin-stat-resolved');
    const elAlerts = document.getElementById('admin-stat-alerts');
    const elAwaiting = document.getElementById('admin-stat-awaiting-verification');
    const elBadgeAwaiting = document.getElementById('badge-awaiting-count');

    if (elTotal) elTotal.textContent = total;
    if (elPending) elPending.textContent = pending;
    if (elProgress) elProgress.textContent = progress;
    if (elResolved) elResolved.textContent = resolved;
    if (elAlerts) elAlerts.textContent = highAlerts;
    if (elAwaiting) elAwaiting.textContent = awaitingList.length;
    if (elBadgeAwaiting) elBadgeAwaiting.textContent = `${awaitingList.length} Grievances`;

    await renderAwaitingVerificationSection(awaitingList);
    renderAdminGrievancesTable();
  } catch (err) {
    console.error('Error loading admin dashboard:', err);
  }
}

function renderAdminGrievancesTable() {
  const tableBody = document.getElementById('admin-grievances-tbody');
  if (!tableBody) return;

  const statusFilter = document.getElementById('admin-filter-status')?.value || 'ALL';
  const categoryFilter = document.getElementById('admin-filter-category')?.value || 'ALL';
  const priorityFilter = document.getElementById('admin-filter-priority')?.value || 'ALL';
  const wardFilter = document.getElementById('admin-filter-ward')?.value || 'ALL';
  const searchTerm = document.getElementById('admin-search-input')?.value.toLowerCase().trim() || '';

  const filtered = allAdminGrievances.filter(g => {
    if (statusFilter !== 'ALL' && g.status !== statusFilter) return false;
    if (categoryFilter !== 'ALL' && g.category !== categoryFilter) return false;
    if (priorityFilter !== 'ALL' && g.priority !== priorityFilter) return false;
    if (wardFilter !== 'ALL' && g.ward_number.toString() !== wardFilter) return false;
    if (searchTerm) {
      const match = g.title.toLowerCase().includes(searchTerm) ||
                    g.tracking_id.toLowerCase().includes(searchTerm) ||
                    g.citizen_name?.toLowerCase().includes(searchTerm) ||
                    g.location_landmark.toLowerCase().includes(searchTerm);
      if (!match) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align:center; padding:2rem; color:#64748B;">
          No matching grievances in records.
        </td>
      </tr>
    `;
    return;
  }

  tableBody.innerHTML = filtered.map(g => {
    const isUrgent = g.priority === 'High';
    const deptOfficerLabel = g.department_name 
      ? `<span style="font-weight:600; font-size:0.8rem; color:#0F5132;">${g.department_code || 'DEPT'}</span>: ${g.officer_name || '<em style="color:#94A3B8;">Unassigned</em>'}${g.worker_name ? `<br><span style="font-size:0.75rem; color:#2563EB; font-weight:600;">🔧 ${escapeHtml(g.worker_name)}</span>` : ''}`
      : `<span style="color:#DC2626; font-size:0.75rem; font-weight:600;">⚠️ Not Assigned</span>`;

    return `
      <tr style="${isUrgent && g.status !== 'RESOLVED' && g.status !== 'CLOSED' ? 'background: #FEF2F2;' : ''}">
        <td>
          <a href="javascript:void(0)" onclick="openGrievanceDetail('${g.tracking_id}')" class="tracking-link">${g.tracking_id}</a>
        </td>
        <td>
          <div style="font-weight:700; color:var(--text-main);">${escapeHtml(g.title)}</div>
          <div style="font-size:0.75rem; color:#64748B;">Ward ${g.ward_number} • ${escapeHtml(g.location_landmark)}</div>
        </td>
        <td>
          <div style="font-weight:600; font-size:0.85rem;">${escapeHtml(g.citizen_name || 'Citizen')}</div>
          <div style="font-size:0.75rem; color:#64748B;">📞 ${escapeHtml(g.citizen_mobile || 'N/A')}</div>
        </td>
        <td>${deptOfficerLabel}</td>
        <td>${getPriorityBadge(g.priority)}</td>
        <td>${getStatusBadge(g.status)}</td>
        <td style="font-size:0.8rem; color:#64748B;">${g.created_at.split(' ')[0]}</td>
        <td>
          <div style="display:flex; gap:0.35rem; align-items:center; flex-wrap:wrap;">
            ${(g.status === 'WORK_COMPLETED' || g.status === 'OFFICER_VERIFICATION') ? `
              <button onclick="openOfficerVerifyModal(${g.id})" class="btn btn-sm btn-accent" style="font-weight:700; background:#D97706; color:#fff;" title="Review Worker Evidence & Verify">
                🔎 Verify Proof
              </button>
            ` : ''}
            ${g.status === 'CITIZEN_VERIFICATION' ? `
              <button onclick="openPhoneVerificationModal(${g.id}, '${g.tracking_id}', '${escapeHtml(g.citizen_name || 'Citizen')}', '${escapeHtml(g.citizen_mobile || '')}')" class="btn btn-sm" style="font-weight:700; background:#0284C7; color:#fff;" title="Development / Mock Verification: Simulate Outbound Call">
                📞 Phone Call
              </button>
            ` : ''}
            <button onclick="openAssignModal(${g.id}, '${g.tracking_id}', ${g.department_id || 'null'}, ${g.assigned_officer_id || 'null'}, ${g.assigned_worker_id || 'null'})" class="btn btn-sm btn-outline-primary" title="Assign Department, Officer & Worker">
              Assign
            </button>
            <button onclick="openStatusUpdateModal(${g.id}, '${g.tracking_id}', '${g.status}')" class="btn btn-sm btn-primary" title="Change Status / Remarks">
              Status
            </button>
            <button onclick="openGrievanceDetail('${g.tracking_id}')" class="btn btn-sm btn-outline" title="Full Timeline History">
              History
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// ==========================================
// ASSIGNMENT MODAL
// ==========================================
async function openAssignModal(id, trackingId, currentDeptId, currentOfficerId, currentWorkerId = null) {
  activeGrievanceForAction = id;
  const elTracking = document.getElementById('assign-modal-tracking-id');
  if (elTracking) elTracking.textContent = trackingId;

  // Clear previous error
  const errBox = document.getElementById('assign-modal-error-box');
  if (errBox) {
    errBox.style.display = 'none';
    errBox.textContent = '';
  }

  // Populate grievance details in review card
  const g = (allAdminGrievances || []).find(item => item.id === id);
  if (g) {
    const elCat = document.getElementById('assign-modal-category');
    if (elCat) elCat.textContent = g.category || 'N/A';

    const elLoc = document.getElementById('assign-modal-location');
    if (elLoc) elLoc.textContent = `Ward ${g.ward_number || 'N/A'} • ${g.location_landmark || 'General'}`;

    const elDate = document.getElementById('assign-modal-date');
    if (elDate) elDate.textContent = g.created_at ? g.created_at.split(' ')[0] : 'N/A';

    const elStatus = document.getElementById('assign-modal-status');
    if (elStatus) elStatus.innerHTML = getStatusBadge(g.status);

    const elTitle = document.getElementById('assign-modal-title');
    if (elTitle) elTitle.textContent = g.title || '';
  }

  const deptSelect = document.getElementById('assign-department-select');
  if (deptSelect && currentDeptId) {
    deptSelect.value = currentDeptId;
  }
  await handleDepartmentSelectChange(currentOfficerId, currentWorkerId);
  openModal('modal-assign-grievance');
}

async function handleDepartmentSelectChange(preselectOfficerId = null, preselectWorkerId = null) {
  const deptSelect = document.getElementById('assign-department-select');
  const officerSelect = document.getElementById('assign-officer-select');
  const workerSelect = document.getElementById('assign-worker-select');
  if (!deptSelect) return;

  const selectedDeptId = parseInt(deptSelect.value);
  if (!selectedDeptId) {
    if (officerSelect) officerSelect.innerHTML = `<option value="">-- First Select Department --</option>`;
    if (workerSelect) workerSelect.innerHTML = `<option value="">-- First Select Department --</option>`;
    return;
  }

  if (officerSelect) {
    const deptOfficers = allOfficers.filter(o => o.department_id === selectedDeptId);
    if (deptOfficers.length === 0) {
      officerSelect.innerHTML = `<option value="">-- No officers registered in this dept --</option>`;
    } else {
      officerSelect.innerHTML = `<option value="">-- Select Field Officer --</option>` +
        deptOfficers.map(o => `
          <option value="${o.id}" ${preselectOfficerId && preselectOfficerId === o.id ? 'selected' : ''}>
            ${escapeHtml(o.full_name)} (${escapeHtml(o.designation)}) [Active: ${o.active_tickets}]
          </option>
        `).join('');
    }
  }

  if (workerSelect) {
    workerSelect.innerHTML = `<option value="">Loading eligible workers...</option>`;
    try {
      const url = activeGrievanceForAction
        ? `/api/grievances/${activeGrievanceForAction}/eligible-workers?department_id=${selectedDeptId}`
        : `/api/workers?department_id=${selectedDeptId}`;
      const res = await fetch(url);
      const data = await res.json();
      const workersList = data.workers || [];

      if (workersList.length === 0) {
        workerSelect.innerHTML = `<option value="">-- No workers found in this department --</option>`;
      } else {
        const minPts = data.min_points_required || 60;
        workerSelect.innerHTML = `<option value="">-- Select Eligible Field Worker --</option>` +
          workersList.map(w => {
            const pts = w.loyalty_points !== undefined ? w.loyalty_points : 100;
            const workload = w.active_workload !== undefined ? w.active_workload : (w.active_tickets !== undefined ? w.active_tickets : 0);
            const isEligible = w.is_eligible !== undefined ? w.is_eligible : (pts >= minPts);
            const reasonStr = !isEligible ? (w.ineligibility_reasons && w.ineligibility_reasons.length ? w.ineligibility_reasons[0] : `Points ${pts} < ${minPts}`) : '';

            return `
              <option value="${w.id}" ${preselectWorkerId && preselectWorkerId === w.id ? 'selected' : ''} ${!isEligible ? 'disabled style="color:#94A3B8; background:#F8FAFC;"' : ''}>
                ${isEligible ? '🔧' : '⛔'} ${escapeHtml(w.full_name)} (${escapeHtml(w.skill_trade)}) [⭐ ${pts} pts | ${workload} Active Tasks] ${!isEligible ? `[INELIGIBLE: ${escapeHtml(reasonStr)}]` : ''}
              </option>
            `;
          }).join('');
      }
    } catch (err) {
      console.error('Error fetching eligible workers:', err);
      const deptWorkers = allWorkers.filter(w => w.department_id === selectedDeptId);
      workerSelect.innerHTML = `<option value="">-- Select Field Worker --</option>` +
        deptWorkers.map(w => {
          const pts = w.loyalty_points !== undefined ? w.loyalty_points : 100;
          const isEligible = pts >= 60;
          return `
            <option value="${w.id}" ${preselectWorkerId && preselectWorkerId === w.id ? 'selected' : ''} ${!isEligible ? 'disabled style="color:#94A3B8;"' : ''}>
              ${isEligible ? '🔧' : '⛔'} ${escapeHtml(w.full_name)} (${escapeHtml(w.skill_trade)}) [⭐ ${pts} pts] ${!isEligible ? '(Ineligible: <60 pts)' : ''}
            </option>
          `;
        }).join('');
    }
  }
}

async function handleAssignSubmit(event) {
  event.preventDefault();
  if (!activeGrievanceForAction) return;

  const departmentId = document.getElementById('assign-department-select').value;
  const officerId = document.getElementById('assign-officer-select')?.value;
  const workerId = document.getElementById('assign-worker-select')?.value;
  const remarks = document.getElementById('assign-remarks').value;
  const errBox = document.getElementById('assign-modal-error-box');
  const submitBtn = document.getElementById('btn-submit-assign');

  if (errBox) {
    errBox.style.display = 'none';
    errBox.textContent = '';
  }

  if (!departmentId) {
    showToast('Please select a responsible department', 'warning');
    return;
  }

  if (!workerId) {
    showToast('Please select an eligible field technician', 'warning');
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Dispatching assignment...';
  }

  try {
    const res = await fetch(`/api/grievances/${activeGrievanceForAction}/assign`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        department_id: departmentId ? parseInt(departmentId) : null,
        assigned_officer_id: officerId ? parseInt(officerId) : null,
        assigned_worker_id: workerId ? parseInt(workerId) : null,
        remarks: remarks || 'Assigned by Panchayat Administration'
      })
    });
    const data = await res.json();
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Confirm & Dispatch Assignment \u2192';
    }

    if (data.success) {
      showToast(data.message, 'success');
      closeModal('modal-assign-grievance');
      await loadAdminDashboard();
      await loadDepartmentsAndOfficers();
    } else {
      if (errBox) {
        errBox.style.display = 'block';
        errBox.textContent = data.error || 'Assignment rejected by system rules.';
      }
      showToast(data.error, 'error');
    }
  } catch (err) {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Confirm & Dispatch Assignment \u2192';
    }
    if (errBox) {
      errBox.style.display = 'block';
      errBox.textContent = 'Failed to assign grievance: ' + err.message;
    }
    showToast('Failed to assign grievance: ' + err.message, 'error');
  }
}


// ==========================================
// STATUS UPDATE MODAL
// ==========================================
function openStatusUpdateModal(id, trackingId, currentStatus) {
  activeGrievanceForAction = id;
  document.getElementById('status-modal-tracking-id').textContent = trackingId;
  const statusSelect = document.getElementById('status-update-select');
  if (statusSelect) {
    statusSelect.value = currentStatus;
  }
  handleStatusSelectChange();
  openModal('modal-status-update');
}

function handleStatusSelectChange() {
  const statusVal = document.getElementById('status-update-select')?.value;
  const resNotesGroup = document.getElementById('status-resnotes-group');
  if (resNotesGroup) {
    resNotesGroup.style.display = (statusVal === 'RESOLVED' || statusVal === 'CLOSED') ? 'block' : 'none';
  }
}

async function handleStatusUpdateSubmit(event) {
  event.preventDefault();
  if (!activeGrievanceForAction) return;

  const newStatus = document.getElementById('status-update-select').value;
  const remarks = document.getElementById('status-remarks').value.trim();
  const resolutionNotes = document.getElementById('status-resolution-notes')?.value.trim();

  if (!remarks) {
    showToast('Official remarks are mandatory for status updates', 'warning');
    return;
  }

  try {
    const res = await fetch(`/api/grievances/${activeGrievanceForAction}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: newStatus,
        remarks: remarks,
        resolution_notes: resolutionNotes
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      closeModal('modal-status-update');
      await loadAdminDashboard();
    } else {
      showToast(data.error, 'error');
    }
  } catch (err) {
    showToast('Error updating status: ' + err.message, 'error');
  }
}

// ==========================================
// ANNOUNCEMENTS MANAGER
// ==========================================
async function loadAnnouncementsManager() {
  const listEl = document.getElementById('admin-announcements-list');
  if (!listEl) return;

  try {
    const res = await fetch('/api/announcements');
    const data = await res.json();
    if (!data.success) return;

    if (data.announcements.length === 0) {
      listEl.innerHTML = `<div style="color:#64748B; padding:1rem; font-size:0.85rem;">No active announcements.</div>`;
      return;
    }

    listEl.innerHTML = data.announcements.map(a => `
      <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:1rem; margin-bottom:0.75rem;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <div style="font-weight:700; color:var(--text-main); font-size:0.95rem;">
              ${a.is_emergency ? '🚨 <span style="color:#DC2626;">[EMERGENCY]</span> ' : ''}${escapeHtml(a.title)}
            </div>
            <div style="font-size:0.75rem; color:#64748B; margin-top:0.2rem;">
              Category: ${a.category} • Published on ${a.created_at.split(' ')[0]} by ${a.published_by_name}
            </div>
          </div>
        </div>
        <p style="font-size:0.85rem; color:#334155; margin-top:0.5rem; line-height:1.4;">${escapeHtml(a.content)}</p>
      </div>
    `).join('');
  } catch (e) {
    console.error('Error loading notices:', e);
  }
}

async function handleAnnouncementSubmit(event) {
  event.preventDefault();
  const form = event.target;
  const title = form.title.value.trim();
  const category = form.category.value;
  const content = form.content.value.trim();
  const isEmergency = form.is_emergency.checked;

  if (!title || !content) {
    showToast('Please provide title and content', 'warning');
    return;
  }

  try {
    const res = await fetch('/api/announcements', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title, category, content, is_emergency: isEmergency
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      form.reset();
      loadAnnouncementsManager();
    } else {
      showToast(data.error, 'error');
    }
  } catch (err) {
    showToast('Failed to post announcement: ' + err.message, 'error');
  }
}

// ==========================================
// OFFICER ROSTER
// ==========================================
function renderOfficerRoster() {
  const container = document.getElementById('officer-roster-tbody');
  if (!container) return;

  container.innerHTML = allOfficers.map(o => `
    <tr>
      <td>
        <div style="font-weight:700; color:var(--text-main);">${escapeHtml(o.full_name)}</div>
        <div style="font-size:0.75rem; color:#64748B;">Badge: <code>${o.badge_id}</code></div>
      </td>
      <td>
        <span class="category-pill">${o.department_name} (${o.department_code})</span>
      </td>
      <td>${escapeHtml(o.designation)}</td>
      <td>📞 ${escapeHtml(o.mobile)}</td>
      <td>
        <span class="badge ${o.active_tickets > 2 ? 'badge-priority-high' : (o.active_tickets > 0 ? 'badge-in_progress' : 'badge-resolved')}">
          ${o.active_tickets} Active Cases
        </span>
      </td>
    </tr>
  `).join('');
}

// ==========================================
// CSV EXPORT GENERATOR
// ==========================================
function exportGrievancesCSV() {
  if (allAdminGrievances.length === 0) {
    showToast('No grievance data to export', 'warning');
    return;
  }

  const headers = ['Tracking ID', 'Title', 'Citizen Name', 'Mobile', 'Ward Number', 'Landmark', 'Category', 'Priority', 'Status', 'Department', 'Officer', 'Created At'];
  const csvRows = [headers.join(',')];

  allAdminGrievances.forEach(g => {
    const row = [
      `"${g.tracking_id}"`,
      `"${(g.title || '').replace(/"/g, '""')}"`,
      `"${(g.citizen_name || '').replace(/"/g, '""')}"`,
      `"${g.citizen_mobile || ''}"`,
      `"${g.ward_number}"`,
      `"${(g.location_landmark || '').replace(/"/g, '""')}"`,
      `"${g.category}"`,
      `"${g.priority}"`,
      `"${g.status}"`,
      `"${(g.department_name || '').replace(/"/g, '""')}"`,
      `"${(g.officer_name || '').replace(/"/g, '""')}"`,
      `"${g.created_at}"`
    ];
    csvRows.push(row.join(','));
  });

  const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.setAttribute('href', url);
  a.setAttribute('download', `GramSeva_Grievances_Report_${new Date().toISOString().slice(0, 10)}.csv`);
  a.click();
  showToast('Gram Panchayat Grievance Report downloaded (CSV)', 'success');
}

// ==========================================
// OFFICER VERIFICATION MODAL & ACTIONS
// ==========================================
let activeVerifyGrievanceId = null;

async function openOfficerVerifyModal(grievanceId) {
  try {
    const res = await fetch(`/api/grievances/${grievanceId}`);
    const data = await res.json();
    if (!data.success) {
      showToast(data.error || 'Failed to load grievance details', 'error');
      return;
    }

    const g = data.grievance;
    activeVerifyGrievanceId = g.id;

    document.getElementById('officer-verify-tracking-id').textContent = g.tracking_id;

    // 1. Original Complaint fields
    document.getElementById('ov-category').innerHTML = `${getCategoryIcon(g.category)} ${escapeHtml(g.category)}`;
    document.getElementById('ov-title').textContent = g.title;
    document.getElementById('ov-location').textContent = `Ward ${g.ward_number} - ${g.location_landmark}`;
    document.getElementById('ov-desc').textContent = g.description;

    const citizenEvBox = document.getElementById('ov-citizen-evidence');
    if (citizenEvBox) {
      if (g.evidence_image) {
        citizenEvBox.innerHTML = `
          <a href="${g.evidence_image}" target="_blank">
            <img src="${g.evidence_image}" style="max-height:120px; border-radius:6px; border:1px solid #CBD5E1; box-shadow:var(--shadow-sm);" />
          </a>
        `;
      } else {
        citizenEvBox.innerHTML = `<span style="font-size:0.78rem; color:#94A3B8; font-style:italic;">No photo attached with complaint</span>`;
      }
    }

    // 2. Worker Completion fields
    const proofs = g.resolution_proofs || [];
    const latestProof = proofs.length > 0 ? proofs[0] : null;

    if (latestProof) {
      document.getElementById('ov-proof-version').textContent = `Attempt #${latestProof.proof_version || 1}`;
      document.getElementById('ov-worker').textContent = `${latestProof.worker_name || 'Assigned Worker'} ${latestProof.worker_trade ? `(${latestProof.worker_trade})` : ''}`;
      document.getElementById('ov-timestamp').textContent = latestProof.created_at;
      document.getElementById('ov-completion-desc').textContent = latestProof.completion_notes || latestProof.description || 'No description provided';
      document.getElementById('ov-remarks').textContent = latestProof.remarks || 'None provided';

      const workerProofBox = document.getElementById('ov-worker-proof');
      if (workerProofBox) {
        let proofHtml = '';
        const isPdf = latestProof.proof_file && latestProof.proof_file.toLowerCase().endsWith('.pdf');
        if (isPdf) {
          proofHtml += `<a href="${latestProof.proof_file}" target="_blank" class="btn btn-sm btn-outline-primary" style="display:inline-flex; align-items:center; gap:0.35rem;">📄 View Proof PDF</a>`;
        } else if (latestProof.proof_file) {
          proofHtml += `<a href="${latestProof.proof_file}" target="_blank"><img src="${latestProof.proof_file}" style="max-height:120px; border-radius:6px; border:1px solid #93C5FD; box-shadow:var(--shadow-sm);" /></a>`;
        }

        if (latestProof.additional_evidence) {
          const isAddPdf = latestProof.additional_evidence.toLowerCase().endsWith('.pdf');
          proofHtml += `<div style="margin-top:0.4rem;">`;
          if (isAddPdf) {
            proofHtml += `<a href="${latestProof.additional_evidence}" target="_blank" class="btn btn-sm btn-outline" style="font-size:0.75rem;">📎 Supporting Document</a>`;
          } else {
            proofHtml += `<a href="${latestProof.additional_evidence}" target="_blank"><img src="${latestProof.additional_evidence}" style="max-height:90px; border-radius:4px; border:1px solid #CBD5E1; margin-top:0.25rem;" /></a>`;
          }
          proofHtml += `</div>`;
        }

        workerProofBox.innerHTML = proofHtml;
      }
    } else {
      document.getElementById('ov-proof-version').textContent = 'No Proof';
      document.getElementById('ov-worker').textContent = g.worker_name || 'Unassigned';
      document.getElementById('ov-timestamp').textContent = 'Pending';
      document.getElementById('ov-completion-desc').textContent = 'No completion report recorded yet.';
      document.getElementById('ov-remarks').textContent = 'N/A';
      document.getElementById('ov-worker-proof').innerHTML = '<span style="color:#94A3B8; font-size:0.8rem;">No uploaded evidence</span>';
    }

    // Reset remarks input
    const remarksEl = document.getElementById('officer-verify-remarks');
    if (remarksEl) remarksEl.value = '';

    openModal('modal-officer-verify');
  } catch (err) {
    showToast('Failed to load verification view: ' + err.message, 'error');
  }
}

async function submitOfficerVerification(decision) {
  if (!activeVerifyGrievanceId) return;

  const remarksInput = document.getElementById('officer-verify-remarks');
  const remarks = (remarksInput?.value || '').trim();

  if (decision === 'REWORK_REQUESTED' && !remarks) {
    showToast('Remarks explaining the rework requirements are mandatory.', 'warning');
    remarksInput?.focus();
    return;
  }

  const defaultRemark = decision === 'APPROVED'
    ? 'Resolution evidence inspected and verified sufficient for citizen check.'
    : 'Rework requested following physical verification review.';
  const finalRemarks = remarks || defaultRemark;

  try {
    const res = await fetch(`/api/grievances/${activeVerifyGrievanceId}/officer-verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        decision: decision,
        remarks: finalRemarks
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      closeModal('modal-officer-verify');
      await loadAdminDashboard();
    } else {
      showToast(data.error || 'Verification action failed', 'error');
    }
  } catch (err) {
    showToast('Failed to submit officer decision: ' + err.message, 'error');
  }
}

// ==========================================
// PHONE / IVR VERIFICATION MODAL (STEP 9)
// Clearly labeled: Development / Mock Verification
// ==========================================
let activePhoneVerificationId = null;

function maskPhoneNumber(phone) {
  if (!phone) return 'N/A';
  const clean = String(phone).replace(/\D/g, '');
  if (clean.length >= 10) {
    return '******' + clean.slice(-4);
  }
  return '******';
}

function openPhoneVerificationModal(id, trackingId, citizenName, citizenMobile) {
  activePhoneVerificationId = id;
  const elTracking = document.getElementById('pv-modal-tracking-id');
  const elCitizen = document.getElementById('pv-modal-citizen-name');
  const elPhone = document.getElementById('pv-modal-phone-ref');
  const elOutcome = document.getElementById('pv-call-outcome');
  const elResp = document.getElementById('pv-citizen-response');
  const elRemarks = document.getElementById('pv-remarks');

  if (elTracking) elTracking.textContent = trackingId;
  if (elCitizen) elCitizen.textContent = citizenName;
  if (elPhone) elPhone.textContent = maskPhoneNumber(citizenMobile);

  if (elOutcome) elOutcome.value = 'ANSWERED';
  if (elResp) elResp.value = 'YES';
  if (elRemarks) elRemarks.value = '';

  handleCallOutcomeChange();
  openModal('modal-phone-verification');
}

function handleCallOutcomeChange() {
  const outcome = document.getElementById('pv-call-outcome')?.value || 'ANSWERED';
  const respGroup = document.getElementById('pv-response-group');
  const helpText = document.getElementById('pv-outcome-help');
  const step2 = document.getElementById('pv-step-2');
  const step3 = document.getElementById('pv-step-3');

  if (step2) {
    step2.style.background = '#DBEAFE';
    step2.style.color = '#1D4ED8';
    step2.textContent = `2. ${outcome}`;
  }

  if (outcome === 'ANSWERED') {
    if (respGroup) respGroup.style.display = 'block';
    if (step3) {
      step3.style.background = '#DBEAFE';
      step3.style.color = '#1D4ED8';
      step3.textContent = '3. Citizen Response';
    }
    if (helpText) {
      helpText.textContent = 'Citizen answered automated call. Citizen response keypad selection applies.';
      helpText.style.color = '#15803D';
    }
  } else {
    if (respGroup) respGroup.style.display = 'none';
    if (step3) {
      step3.style.background = '#F1F5F9';
      step3.style.color = '#94A3B8';
      step3.textContent = '3. No Response (Skipped)';
    }
    if (helpText) {
      if (outcome === 'NO_ANSWER' || outcome === 'BUSY') {
        helpText.textContent = `Rule: Non-answered calls (${outcome}) are NEVER interpreted as NO. Grievance status remains in CITIZEN_VERIFICATION.`;
        helpText.style.color = '#D97706';
      } else {
        helpText.textContent = `Call could not be completed (${outcome}). Grievance status remains in CITIZEN_VERIFICATION.`;
        helpText.style.color = '#DC2626';
      }
    }
  }
}

async function handlePhoneVerificationSubmit(event) {
  event.preventDefault();
  if (!activePhoneVerificationId) return;

  const outcome = document.getElementById('pv-call-outcome')?.value || 'ANSWERED';
  const response = outcome === 'ANSWERED' ? document.getElementById('pv-citizen-response')?.value : null;
  const remarks = document.getElementById('pv-remarks')?.value.trim();

  const submitBtn = document.getElementById('pv-submit-btn');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = '📞 Placing Mock Call...';
  }

  try {
    const res = await fetch(`/api/grievances/${activePhoneVerificationId}/trigger-verification-call`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        simulated_outcome: outcome,
        simulated_response: response,
        remarks: remarks
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`[Mock Verification] Outcome: ${data.call_result.call_outcome} -> Status: ${data.status}`, 'success');
      closeModal('modal-phone-verification');
      await loadAdminDashboard();
    } else {
      showToast(data.error || 'Phone verification simulation failed', 'error');
    }
  } catch (err) {
    showToast('Network error during phone simulation: ' + err.message, 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = '📞 Run Mock Call Simulation';
    }
  }
}

// ==========================================
// STEP 10: OFFICER DOUBLE VERIFICATION
// ==========================================
function scrollToAwaitingVerification() {
  const el = document.getElementById('officer-awaiting-verification-section');
  if (el) el.scrollIntoView({ behavior: 'smooth' });
}

async function renderAwaitingVerificationSection(awaitingList) {
  const container = document.getElementById('awaiting-verification-container');
  if (!container) return;

  if (!awaitingList || awaitingList.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding:2rem 1rem; color:#64748B;">
        <div style="font-size:2.2rem; margin-bottom:0.4rem;">✅</div>
        <div style="font-weight:700; color:#1E293B; font-size:1.05rem;">No Grievances Currently Awaiting Officer Verification</div>
        <p style="font-size:0.85rem; margin-top:0.25rem; color:#64748B; max-width:500px; margin-left:auto; margin-right:auto;">
          When field workers complete remediation work and upload proof, grievances will appear here for review and verification approval.
        </p>
      </div>
    `;
    return;
  }

  // Fetch full details for awaiting grievances to retrieve resolution proofs and remarks
  const detailedList = await Promise.all(
    awaitingList.map(async (g) => {
      try {
        const res = await fetch(`/api/grievances/${g.id}`);
        const data = await res.json();
        return (data.success && data.grievance) ? data.grievance : g;
      } catch (e) {
        return g;
      }
    })
  );

  container.innerHTML = detailedList.map(g => {
    const latestProof = (g.resolution_proofs && g.resolution_proofs.length > 0) ? g.resolution_proofs[0] : null;
    const isPdf = latestProof && latestProof.proof_file && latestProof.proof_file.toLowerCase().endsWith('.pdf');

    return `
      <div class="officer-verify-card" id="ov-card-${g.id}" style="border: 1.5px solid #FCD34D; background: #FFFFFF; border-radius: 10px; padding: 1.25rem; margin-bottom: 1.25rem; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
        <!-- Card Header -->
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-bottom:1rem; border-bottom:1px solid #E2E8F0; padding-bottom:0.6rem;">
          <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
            <a href="javascript:void(0)" onclick="openGrievanceDetail('${g.tracking_id}')" class="tracking-link" style="font-size:1.1rem; font-weight:800; font-family:monospace;">${g.tracking_id}</a>
            <span class="category-pill">${getCategoryIcon(g.category)} ${escapeHtml(g.category)}</span>
            ${getPriorityBadge(g.priority)}
            ${getStatusBadge(g.status)}
          </div>
          <div style="font-size:0.8rem; color:#64748B;">
            Submitted: ${g.created_at ? g.created_at.split(' ')[0] : 'N/A'}
          </div>
        </div>

        <!-- 2 Column Details: Original Complaint vs Worker Proof & Remarks -->
        <div class="officer-verify-grid">
          <!-- Column 1: Original Complaint -->
          <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:1rem;">
            <div style="font-size:0.78rem; font-weight:800; color:#1E40AF; text-transform:uppercase; margin-bottom:0.4rem; display:flex; align-items:center; gap:0.35rem;">
              <span>📋</span> Original Complaint
            </div>
            <div style="font-weight:700; color:#0F172A; font-size:1rem; margin-bottom:0.35rem;">
              ${escapeHtml(g.title)}
            </div>
            <div style="font-size:0.88rem; color:#334155; line-height:1.45; margin-bottom:0.6rem;">
              ${escapeHtml(g.description)}
            </div>
            <div style="font-size:0.8rem; color:#64748B; border-top:1px dashed #CBD5E1; padding-top:0.5rem;">
              <div>📍 <strong>Location:</strong> Ward ${g.ward_number} • ${escapeHtml(g.location_landmark)}</div>
              <div style="margin-top:0.2rem;">👤 <strong>Citizen:</strong> ${escapeHtml(g.citizen_name || 'Citizen')} (📞 ${escapeHtml(g.citizen_mobile || 'N/A')})</div>
            </div>
            ${g.evidence_image ? `
              <div style="margin-top:0.6rem; border-top:1px dashed #CBD5E1; padding-top:0.5rem;">
                <div style="font-size:0.75rem; font-weight:700; color:#475569; margin-bottom:0.25rem;">📷 Citizen Evidence Photo:</div>
                <a href="${g.evidence_image}" target="_blank">
                  <img src="${g.evidence_image}" alt="Citizen Evidence" style="max-height:100px; border-radius:6px; border:1px solid #CBD5E1;" />
                </a>
              </div>
            ` : ''}
          </div>

          <!-- Column 2: Worker Proof & Worker Remarks -->
          <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:1rem;">
            <div style="font-size:0.78rem; font-weight:800; color:#15803D; text-transform:uppercase; margin-bottom:0.4rem; display:flex; align-items:center; gap:0.35rem;">
              <span>🛠️</span> Worker Proof & Remarks
            </div>
            ${latestProof ? `
              <div style="font-size:0.88rem; color:#14532D; margin-bottom:0.5rem;">
                <strong>Work Completion Description:</strong>
                <div style="background:#FFFFFF; padding:0.5rem 0.75rem; border-radius:6px; border:1px solid #DCFCE7; margin-top:0.25rem; font-style:italic;">
                  "${escapeHtml(latestProof.completion_notes || latestProof.description || 'Remediation completed')}"
                </div>
              </div>

              ${latestProof.remarks ? `
                <div style="font-size:0.84rem; color:#166534; margin-bottom:0.4rem;">
                  <strong>Worker Resolution Remarks:</strong> ${escapeHtml(latestProof.remarks)}
                </div>
              ` : ''}

              <div style="font-size:0.8rem; color:#475569; margin-bottom:0.5rem;">
                👤 <strong>Worker:</strong> ${escapeHtml(latestProof.worker_name || 'Assigned Worker')} ${latestProof.worker_trade ? `(${escapeHtml(latestProof.worker_trade)})` : ''} • 📅 ${latestProof.created_at}
                ${latestProof.location_coords ? `<br>📍 <strong>GPS Location:</strong> ${escapeHtml(latestProof.location_coords)}` : ''}
              </div>

              <div style="margin-top:0.5rem; border-top:1px dashed #86EFAC; padding-top:0.5rem;">
                <div style="font-size:0.75rem; font-weight:700; color:#15803D; margin-bottom:0.3rem;">Worker Uploaded Proof:</div>
                ${isPdf ? `
                  <a href="${latestProof.proof_file}" target="_blank" class="btn btn-sm btn-outline-primary" style="display:inline-flex; align-items:center; gap:0.3rem;">
                    📄 View Proof Document (PDF)
                  </a>
                ` : `
                  <a href="${latestProof.proof_file}" target="_blank">
                    <img src="${latestProof.proof_file}" alt="Resolution Proof" style="max-height:120px; border-radius:6px; border:1px solid #CBD5E1;" />
                  </a>
                `}
              </div>
            ` : `
              <div style="color:#64748B; font-style:italic; font-size:0.85rem;">
                No formal proof record attached.
              </div>
            `}
          </div>
        </div>

        <!-- Verification Controls -->
        <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:8px; padding:1rem; margin-top:0.5rem;">
          <div style="font-weight:700; font-size:0.88rem; color:#92400E; margin-bottom:0.35rem; display:flex; align-items:center; gap:0.4rem;">
            <span>⚖️</span> Officer Verification Decision Controls
          </div>
          <div class="form-group" style="margin-bottom:0.85rem;">
            <label for="officer-remarks-${g.id}" class="form-label" style="font-size:0.82rem; font-weight:600; color:#78350F;">
              Officer Verification Remarks <span class="required">*</span>
            </label>
            <textarea id="officer-remarks-${g.id}" class="form-control" rows="2" placeholder="Document audit observations or specific rework required (mandatory)..."></textarea>
          </div>
          <div style="display:flex; gap:0.75rem; flex-wrap:wrap; align-items:center;">
            <button type="button" onclick="submitOfficerVerification(${g.id}, 'APPROVED')" class="btn touch-btn" style="background:#16A34A; color:#FFFFFF; border:none; padding:0.65rem 1.25rem; font-weight:700; flex:1; min-width:240px; justify-content:center;">
              ✓ Approve for Citizen Verification
            </button>
            <button type="button" onclick="submitOfficerVerification(${g.id}, 'REWORK_REQUESTED')" class="btn touch-btn" style="background:#DC2626; color:#FFFFFF; border:none; padding:0.65rem 1.25rem; font-weight:700; flex:1; min-width:180px; justify-content:center;">
              🔁 Request Rework
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

async function openOfficerVerifyModal(grievanceId) {
  try {
    const res = await fetch(`/api/grievances/${grievanceId}`);
    const data = await res.json();
    if (!data.success || !data.grievance) {
      showToast('Failed to load grievance details', 'error');
      return;
    }

    const g = data.grievance;
    document.getElementById('ov-modal-grievance-id').value = g.id;
    document.getElementById('ov-modal-tracking-id').textContent = g.tracking_id;
    document.getElementById('ov-original-title').textContent = g.title;
    document.getElementById('ov-original-desc').textContent = g.description;
    document.getElementById('ov-original-meta').textContent = `Ward ${g.ward_number} • ${g.location_landmark} • Citizen: ${g.citizen_name || 'Citizen'} (${g.citizen_mobile || 'N/A'})`;

    const evBox = document.getElementById('ov-original-evidence');
    if (g.evidence_image) {
      evBox.style.display = 'block';
      evBox.innerHTML = `<strong>Citizen Evidence:</strong><br><a href="${g.evidence_image}" target="_blank"><img src="${g.evidence_image}" style="max-height:120px; border-radius:6px; margin-top:4px;" /></a>`;
    } else {
      evBox.style.display = 'none';
      evBox.innerHTML = '';
    }

    const latestProof = (g.resolution_proofs && g.resolution_proofs.length > 0) ? g.resolution_proofs[0] : null;
    if (latestProof) {
      document.getElementById('ov-worker-notes').textContent = `"${latestProof.completion_notes || latestProof.description || 'Work completed'}"`;
      document.getElementById('ov-worker-remarks-block').innerHTML = latestProof.remarks ? `<strong>Worker Remarks:</strong> ${escapeHtml(latestProof.remarks)}` : '';
      document.getElementById('ov-worker-meta').textContent = `Uploaded by: ${latestProof.worker_name || 'Worker'} (${latestProof.worker_trade || 'Field Staff'}) • ${latestProof.created_at}`;

      const isPdf = latestProof.proof_file && latestProof.proof_file.toLowerCase().endsWith('.pdf');
      document.getElementById('ov-worker-proof-files').innerHTML = isPdf
        ? `<a href="${latestProof.proof_file}" target="_blank" class="btn btn-sm btn-outline-primary">📄 View Proof PDF</a>`
        : `<a href="${latestProof.proof_file}" target="_blank"><img src="${latestProof.proof_file}" style="max-height:140px; border-radius:6px; border:1px solid #CBD5E1;" /></a>`;
    } else {
      document.getElementById('ov-worker-notes').textContent = 'No formal proof record found.';
      document.getElementById('ov-worker-remarks-block').innerHTML = '';
      document.getElementById('ov-worker-meta').textContent = '';
      document.getElementById('ov-worker-proof-files').innerHTML = '';
    }

    document.getElementById('ov-modal-remarks').value = '';
    openModal('modal-officer-verify');
  } catch (err) {
    showToast('Error opening verification modal: ' + err.message, 'error');
  }
}

async function submitOfficerModalVerification(decision) {
  const grievanceId = document.getElementById('ov-modal-grievance-id').value;
  const remarks = document.getElementById('ov-modal-remarks').value.trim();
  if (!remarks) {
    showToast('Officer verification remarks are mandatory.', 'warning');
    document.getElementById('ov-modal-remarks').focus();
    return;
  }
  await executeOfficerVerification(grievanceId, decision, remarks, 'modal-officer-verify');
}

async function submitOfficerVerification(grievanceId, decision) {
  const remarksInput = document.getElementById(`officer-remarks-${grievanceId}`);
  const remarks = remarksInput ? remarksInput.value.trim() : '';
  if (!remarks) {
    showToast('Officer verification remarks are mandatory.', 'warning');
    if (remarksInput) remarksInput.focus();
    return;
  }
  await executeOfficerVerification(grievanceId, decision, remarks, null);
}

async function executeOfficerVerification(grievanceId, decision, remarks, modalToClose) {
  try {
    const res = await fetch(`/api/grievances/${grievanceId}/officer-verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, remarks })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      if (modalToClose) closeModal(modalToClose);
      await loadAdminDashboard();
    } else {
      showToast(data.error || 'Verification failed', 'error');
    }
  } catch (err) {
    showToast('Error executing officer verification: ' + err.message, 'error');
  }
}

