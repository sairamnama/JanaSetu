/**
 * GramSeva - Rural Panchayat Grievance Redressal System
 * Core Client Application Logic & Utility Engine
 */

// ==========================================
// 1. MULTILINGUAL TRANSLATION SYSTEM
// ==========================================
// Authoritative translation dictionary is loaded from translations.js
const TRANSLATIONS = window.TRANSLATIONS || {};
let currentLang = window.currentLang || (typeof localStorage !== 'undefined' && localStorage.getItem('gramseva_lang')) || 'en';

function setLanguage(lang) {
  if (typeof window.setLanguage === 'function') {
    return window.setLanguage(lang);
  }
}

// ==========================================
// 2. TOAST NOTIFICATIONS MANAGER
// ==========================================
function showToast(message, type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  const indicator = `<span class="toast-indicator toast-indicator-${type}" aria-hidden="true"></span>`;
  toast.innerHTML = `${indicator}<div>${message}</div>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ==========================================
// 3. DEMO ROLE SWITCHER ENGINE
// ==========================================
async function switchDemoRole(role) {
  try {
    const res = await fetch('/api/demo-switch-user', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      setTimeout(() => {
        if (role === 'admin' || role === 'officer') {
          window.location.href = '/admin';
        } else if (role === 'worker') {
          window.location.href = '/worker';
        } else {
          window.location.href = '/citizen';
        }
      }, 400);
    } else {
      showToast(data.error, 'error');
    }
  } catch (err) {
    showToast('Failed to switch persona: ' + err.message, 'error');
  }
}

// ==========================================
// 4. AUTHENTICATION STATE & NAVBAR UI
// ==========================================
let currentUser = null;

async function checkAuth() {
  try {
    const res = await fetch('/api/current-user');
    const data = await res.json();
    currentUser = data.user;
    updateNavbarUser(data.user);
    return data.user;
  } catch (e) {
    return null;
  }
}

function updateNavbarUser(user) {
  window.currentUser = user;
  const userArea = document.getElementById('navbar-user-area');
  if (!userArea) return;

  const t = typeof window.t === 'function' ? window.t : function(k, d) { return d || k; };

  if (user) {
    const roleBadgeClass = user.role === 'admin' ? 'badge-priority-high' :
                           (user.role === 'officer' ? 'badge-assigned' :
                           (user.role === 'worker' ? 'badge-work_completed' : 'badge-submitted'));
    const roleLabel = t('role_' + user.role, user.role);
    const wardText = user.ward_number ? ' • ' + t('lbl_ward', 'Ward') + ' ' + user.ward_number : '';
    userArea.innerHTML = `
      <div style="display:flex; align-items:center; gap:0.75rem;">
        <div style="text-align:right;">
          <div style="font-weight:700; font-size:0.85rem; color:var(--civic-dark);">${escapeHtml(user.full_name)}</div>
          <div style="font-size:0.75rem; color:var(--text-muted); text-transform:capitalize;">
            <span class="badge ${roleBadgeClass}">${roleLabel}</span>
            ${wardText}
          </div>
        </div>
        <button onclick="handleLogout()" class="btn btn-outline btn-sm" title="${t('sign_out', 'Sign Out')}">${t('sign_out', 'Sign Out')}</button>
      </div>
    `;
  } else {
    userArea.innerHTML = `
      <div style="display:flex; gap:0.4rem; align-items:center; flex-wrap:wrap;">
        <a href="/citizen/login" class="btn btn-outline-primary btn-sm">${t('btn_sign_in_citizen', 'Citizen Login')}</a>
        <a href="/worker/login" class="btn btn-outline btn-sm">${t('btn_sign_in_worker', 'Worker Login')}</a>
        <a href="/admin/login" class="btn btn-outline btn-sm">${t('btn_sign_in_admin', 'Admin Login')}</a>
      </div>
    `;
  }
}

async function handleLogout() {
  await fetch('/api/logout', { method: 'POST' });
  showToast(typeof window.t === 'function' ? window.t('msg_logout_success', 'Logged out successfully') : 'Logged out successfully', 'success');
  setTimeout(() => window.location.href = '/', 400);
}

// ==========================================
// 5. STATUS & BADGE FORMATTERS
// ==========================================
function getStatusBadge(status) {
  const normStatus = (status || '').toUpperCase().trim();
  // Status badge with clean CSS indicator dot (replaces decorative emojis)






  const classMap = {
    'SUBMITTED': 'badge-submitted', 'UNDER_REVIEW': 'badge-review', 'ACCEPTED': 'badge-accepted',
    'ASSIGNED': 'badge-assigned', 'IN_PROGRESS': 'badge-in_progress', 'WORK_COMPLETED': 'badge-work_completed',
    'OFFICER_VERIFICATION': 'badge-officer_verification', 'CITIZEN_VERIFICATION': 'badge-citizen_verification',
    'VERIFIED': 'badge-verified', 'RESOLVED': 'badge-resolved', 'CLOSED': 'badge-closed',
    'REWORK_REQUIRED': 'badge-rework_required', 'REOPENED': 'badge-reopened', 'ESCALATED': 'badge-escalated',
    'REJECTED': 'badge-rejected'
  };

  const badgeCls = classMap[normStatus] || 'badge-submitted';
  const transKey = 'status_' + normStatus.toLowerCase();
  const label = typeof window.t === 'function' ? window.t(transKey, normStatus) : normStatus;
  return `<span class="badge ${badgeCls}" aria-label="Status: ${label}"><span class="badge-dot" aria-hidden="true"></span>${label}</span>`;
}

function getPriorityBadge(priority) {
  const p = (priority || '').toLowerCase();
  let key = 'priority_low';
  let cls = 'badge-priority-low';
  if (p === 'high' || p === 'urgent') {
    key = 'priority_high';
    cls = 'badge-priority-high';
  } else if (p === 'medium') {
    key = 'priority_medium';
    cls = 'badge-priority-medium';
  }
  const label = typeof window.t === 'function' ? window.t(key, priority) : priority;
  return `<span class="badge ${cls}" aria-label="Priority: ${label}">${label}</span>`;
}

function getCategoryIcon(cat) {
  return '';
}

function getCategoryLabel(cat) {
  if (!cat) return '';
  const c = cat.toLowerCase();
  if (typeof window.t === 'function') {
    if (c.includes('water')) return window.t('cat_water', cat);
    if (c.includes('street') || c.includes('light') || c.includes('electr')) return window.t('cat_streetlights', cat);
    if (c.includes('sanitat') || c.includes('waste') || c.includes('drain')) return window.t('cat_sanitation', cat);
    if (c.includes('road')) return window.t('cat_roads', cat);
    if (c.includes('health')) return window.t('cat_health', cat);
    if (c.includes('school') || c.includes('angan')) return window.t('cat_schools', cat);
    if (c.includes('welfare') || c.includes('pension')) return window.t('cat_welfare', cat);
  }
  return cat;
}

// ==========================================
// 6. MODAL UTILITY HELPERS
// ==========================================
function openModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.add('active');
}

function closeModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.remove('active');
}

// Quick tracking input handler
function handleQuickTrack(event) {
  if (event) event.preventDefault();
  const input = document.getElementById('quick-track-input');
  if (!input) return;
  const val = input.value.trim().toUpperCase();
  if (!val) {
    showToast('Please enter a Grievance Tracking ID', 'warning');
    return;
  }
  window.location.href = `/track/${encodeURIComponent(val)}`;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#039;');
}

function printReceipt() {
  window.print();
}

// 7-Stage Double Verification Lifecycle Stepper Renderer (Step 10)
function renderTimelineStepper(currentStatus) {
  window._lastTimelineStatus = currentStatus;
  const t = typeof window.t === 'function' ? window.t : function(k, d) { return d || k; };
  const stages = [
    { num: 1, label: t('step_submitted', 'Complaint Submitted') },
    { num: 2, label: t('step_assigned', 'Assigned') },
    { num: 3, label: t('step_progress', 'Work in Progress') },
    { num: 4, label: t('step_work_completed', 'Work Completed') },
    { num: 5, label: t('step_officer_verif', 'Officer Verified') },
    { num: 6, label: t('step_citizen_verif', 'Citizen Verification') },
    { num: 7, label: t('step_resolved', 'Resolved') }
  ];

  const statusToStage = {
    'SUBMITTED': 1,
    'UNDER_REVIEW': 1,
    'ACCEPTED': 1,
    'ASSIGNED': 2,
    'IN_PROGRESS': 3,
    'WORK_COMPLETED': 4,
    'OFFICER_VERIFICATION': 5,
    'CITIZEN_VERIFICATION': 6,
    'VERIFIED': 6,
    'RESOLVED': 7,
    'CLOSED': 7,
    'REWORK_REQUIRED': 4,
    'REOPENED': 6,
    'ESCALATED': 4,
    'REJECTED': 0
  };


  const currentStage = statusToStage[currentStatus] || 1;
  const stepperEl = document.getElementById('timeline-stepper-container');
  if (!stepperEl) return;

  if (currentStatus === 'REJECTED') {
    stepperEl.innerHTML = `
      <div style="background:#FEE2E2; border:1px solid #FCA5A5; color:#991B1B; padding:1rem; border-radius:8px; text-align:center; font-weight:700;">
        This grievance was rejected after Panchayat verification.
      </div>
    `;
    return;
  }

  const activeStageObj = stages.find(s => s.num === currentStage) || stages[0];
  let stageModifierNote = '';
  if (currentStatus === 'REWORK_REQUIRED') {
    stageModifierNote = '<span style="background:#FEF3C7; color:#92400E; padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; margin-left:6px;">Rework in Progress</span>';
  } else if (currentStatus === 'REOPENED') {
    stageModifierNote = '<span style="background:#FCE7F3; color:#BE185D; padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; margin-left:6px;">Reopened by Citizen</span>';
  } else if (currentStatus === 'ESCALATED') {
    stageModifierNote = '<span style="background:#FEE2E2; color:#B91C1C; padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; margin-left:6px;">Administratively Escalated</span>';
  }

  let html = `
    <div class="double-verif-card" role="region" aria-label="Double Verification Lifecycle">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem; border-bottom:1px solid #DCE4DE; padding-bottom:0.5rem; flex-wrap:wrap; gap:0.5rem;">
        <div style="font-weight:700; font-size:0.85rem; color:#10533C;">
          <strong>Double Verification Grievance Lifecycle</strong>
        </div>
        <div style="font-size:0.8rem; color:#5D6B63;">
          Current State: <strong style="color:#176B68;">${activeStageObj.label}</strong> ${stageModifierNote}
        </div>
      </div>
      <div class="double-verif-stepper">
  `;

  stages.forEach((st, idx) => {
    const isCompleted = st.num < currentStage;
    const isActive = st.num === currentStage;
    const stateClass = isCompleted ? 'completed' : (isActive ? 'active' : 'pending');
    const isWarning = (currentStatus === 'REWORK_REQUIRED' && st.num === 4) ||
                      (currentStatus === 'REOPENED' && st.num === 6) ||
                      (currentStatus === 'ESCALATED' && st.num === 4);

    const circleContent = isCompleted ? '✓' : st.num;
    const badgeText = isActive ? (isWarning ? 'Active (Issue)' : 'Current State') : (isCompleted ? 'Done' : '');

    html += `
      <div class="dv-step ${stateClass} ${isWarning ? 'warning' : ''}" aria-current="${isActive ? 'step' : 'false'}">
        <div class="dv-step-circle" title="Step ${st.num}: ${st.label}">${circleContent}</div>
        <div class="dv-step-title">${st.label}</div>
        ${badgeText ? `<span class="dv-step-badge">${badgeText}</span>` : ''}
      </div>
    `;

    if (idx < stages.length - 1) {
      html += '<div class="dv-arrow" aria-hidden="true">→</div>';
    }
  });

  html += `
      </div>
    </div>
  `;

  stepperEl.innerHTML = html;
}

// Global Grievance Detail & Timeline Modal Opener
async function openGrievanceDetail(idOrTracking) {
  try {
    const res = await fetch(`/api/grievances/${idOrTracking}`);
    const data = await res.json();
    if (!data.success) {
      showToast(data.error || 'Grievance not found', 'error');
      return;
    }

    const g = data.grievance;
    const modal = document.getElementById('modal-grievance-detail');
    if (!modal) return;

    renderTimelineStepper(g.status);

    document.getElementById('detail-tracking-id').textContent = g.tracking_id;
    document.getElementById('detail-title').textContent = g.title;
    document.getElementById('detail-category').innerHTML = `<span class="category-pill">${escapeHtml(g.category)}</span>`;
    document.getElementById('detail-ward').textContent = `Ward ${g.ward_number} - ${g.location_landmark}`;
    document.getElementById('detail-priority').innerHTML = getPriorityBadge(g.priority);
    document.getElementById('detail-status').innerHTML = getStatusBadge(g.status);
    document.getElementById('detail-desc').textContent = g.description;
    document.getElementById('detail-citizen').textContent = `${g.citizen_name || 'Citizen'} (${g.citizen_mobile || 'N/A'})`;
    document.getElementById('detail-date').textContent = g.created_at;

    const deptOfficerEl = document.getElementById('detail-dept-officer');
    if (deptOfficerEl) {
      if (g.department_name) {
        deptOfficerEl.innerHTML = `
          <strong>${escapeHtml(g.department_name)}</strong><br>
          ${g.officer_name ? `Officer: <span style="color:#176B4D; font-weight:600;">${escapeHtml(g.officer_name)}</span> (${escapeHtml(g.officer_designation || 'Field Official')})` : '<em>Officer unassigned</em>'}
          ${g.worker_name ? `<br>Worker: <span style="color:#176B4D; font-weight:600;">${escapeHtml(g.worker_name)}</span> (${escapeHtml(g.worker_trade || 'Field Technician')})` : ''}
        `;
      } else {
        deptOfficerEl.innerHTML = `<em>Department not yet assigned</em>`;
      }
    }

    const evidenceContainer = document.getElementById('detail-evidence-container');
    if (evidenceContainer) {
      let evHtml = '';
      if (g.evidence_image) {
        evHtml += `
          <div style="margin-top:0.75rem;">
            <div style="font-weight:600; font-size:0.85rem; margin-bottom:0.4rem;">Citizen Evidence Photo:</div>
            <a href="${g.evidence_image}" target="_blank">
              <img src="${g.evidence_image}" style="max-height:160px; border-radius:8px; border:1px solid #DCE4DE; box-shadow:var(--shadow-sm);" />
            </a>
          </div>
        `;
      }
      evidenceContainer.innerHTML = evHtml;
    }

    // Step 4 UI: Dedicated Worker Resolution Proof Section & Verification Banner
    const workerProofContainer = document.getElementById('detail-worker-proof-container');
    if (workerProofContainer) {
      if (g.resolution_proofs && g.resolution_proofs.length > 0) {
        let proofSectionHtml = '';

        // Prominent Status Banner
        if (g.status === 'WORK_COMPLETED' || g.status === 'OFFICER_VERIFICATION') {
          proofSectionHtml += `
            <div class="awaiting-verification-banner" style="background:#E8F3ED; border:2px solid #176B68; color:#176B4D; font-weight:800; padding:0.75rem 1rem; border-radius:8px; margin:1rem 0; display:flex; align-items:center; gap:0.6rem; font-size:0.95rem; box-shadow:0 1px 3px rgba(37,99,235,0.15);">
              WORK COMPLETED — AWAITING VERIFICATION
            </div>
          `;
        }

        proofSectionHtml += `
          <div class="card worker-proof-card" style="margin-top:1rem; border:1px solid #DCE4DE; background:#F8F7F2; border-radius:10px; padding:1.1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1.5px solid #DCE4DE; padding-bottom:0.6rem; margin-bottom:0.85rem;">
              <h4 style="font-size:1rem; color:#1E3A8A; font-weight:700; margin:0; display:flex; align-items:center; gap:0.4rem;">
                Worker Resolution Proof
              </h4>
              <div style="font-size:0.8rem;">
                <span style="color:#5D6B63;">Current Status:</span> ${getStatusBadge(g.status)}
              </div>
            </div>
        `;

        proofSectionHtml += g.resolution_proofs.map((proof, idx) => {
          const isPdf = proof.proof_file && proof.proof_file.toLowerCase().endsWith('.pdf');
          const isAddPdf = proof.additional_evidence && proof.additional_evidence.toLowerCase().endsWith('.pdf');

          return `
            <div style="background:#FFFFFF; border:1px solid #DCE4DE; border-radius:8px; padding:0.9rem; margin-bottom:${idx === g.resolution_proofs.length - 1 ? '0' : '0.75rem'};">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                <div style="font-weight:700; font-size:0.85rem; color:#176B4D;">
                  Proof Attempt #${proof.proof_version || (g.resolution_proofs.length - idx)}
                  ${(proof.proof_version > 1 || idx > 0) ? '<span style="background:#FEF3C7; color:#92400E; padding:2px 6px; border-radius:4px; font-size:0.72rem; margin-left:4px;">Rework Submission</span>' : ''}
                </div>
                <div style="font-size:0.78rem; color:#5D6B63;">
                  ${proof.created_at}
                </div>
              </div>

              <div style="font-size:0.85rem; color:#5D6B63; margin-bottom:0.5rem; line-height:1.5;">
                <strong style="color:#5D6B63;">Description:</strong>
                <div style="background:#E8F3ED; border-radius:6px; padding:0.6rem; margin-top:0.25rem; font-style:italic;">
                  "${escapeHtml(proof.completion_notes || proof.description || '')}"
                </div>
              </div>

              ${proof.remarks ? `
              <div style="font-size:0.83rem; color:#5D6B63; margin-bottom:0.5rem;">
                <strong style="color:#5D6B63;">Resolution Remarks:</strong> ${escapeHtml(proof.remarks)}
              </div>` : ''}

              ${proof.location_coords ? `
              <div style="font-size:0.82rem; color:#5D6B63; margin-bottom:0.5rem;">
                <strong>Work Location:</strong> ${escapeHtml(proof.location_coords)}
              </div>` : ''}

              <div style="font-size:0.82rem; color:#5D6B63; margin-bottom:0.6rem;">
                <strong>Uploaded by:</strong> ${escapeHtml(proof.worker_name || 'Assigned Worker')} ${proof.worker_trade ? `(${escapeHtml(proof.worker_trade)})` : ''}
              </div>

              <!-- Evidence Photos / Documents -->
              <div style="margin-top:0.6rem;">
                <div style="font-weight:600; font-size:0.82rem; color:#5D6B63; margin-bottom:0.35rem;">Evidence Attachment:</div>
                <div style="display:flex; flex-wrap:wrap; gap:0.75rem; align-items:flex-start;">
                  <div>
                    ${isPdf ? `
                      <a href="${proof.proof_file}" target="_blank" class="btn btn-sm btn-outline-primary" style="display:inline-flex; align-items:center; gap:0.35rem;">
                        View Proof PDF Document
                      </a>
                    ` : `
                      <a href="${proof.proof_file}" target="_blank">
                        <img src="${proof.proof_file}" style="max-height:160px; max-width:100%; border-radius:6px; border:1px solid #DCE4DE; box-shadow:var(--shadow-sm); display:block;" alt="Resolution Proof" />
                      </a>
                    `}
                  </div>
                  ${proof.additional_evidence ? `
                    <div>
                      <div style="font-size:0.75rem; color:#5D6B63; margin-bottom:0.2rem;">Additional Supporting Evidence:</div>
                      ${isAddPdf ? `
                        <a href="${proof.additional_evidence}" target="_blank" class="btn btn-sm btn-outline" style="display:inline-flex; align-items:center; gap:0.35rem;">
                          Supporting Document (PDF)
                        </a>
                      ` : `
                        <a href="${proof.additional_evidence}" target="_blank">
                          <img src="${proof.additional_evidence}" style="max-height:120px; border-radius:6px; border:1px solid #DCE4DE;" alt="Additional Evidence" />
                        </a>
                      `}
                    </div>
                  ` : ''}
                </div>
              </div>
            </div>
          `;
        }).join('');

        if (currentUser && (currentUser.role === 'officer' || currentUser.role === 'admin') && (g.status === 'WORK_COMPLETED' || g.status === 'OFFICER_VERIFICATION')) {
          proofSectionHtml += `
            <div style="background:#FEF3C7; border:1px solid #FCD34D; border-radius:8px; padding:0.85rem 1rem; margin-top:0.85rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
              <div>
                <div style="font-weight:700; color:#92400E; font-size:0.85rem;">Officer Action Required:</div>
                <div style="font-size:0.8rem; color:#78350F;">Review worker remediation proof and decide next workflow step.</div>
              </div>
              <button onclick="closeModal('modal-grievance-detail'); if(typeof openOfficerVerifyModal==='function') { openOfficerVerifyModal(${g.id}); } else { window.location.href='/admin'; }" class="btn btn-sm btn-accent" style="background:#D97706; color:#fff; font-weight:700;">
                Conduct Officer Verification
              </button>
            </div>
          `;
        }

        proofSectionHtml += `</div>`;
        workerProofContainer.innerHTML = proofSectionHtml;
      } else {
        workerProofContainer.innerHTML = '';
      }
    }

    // Step 6 UI: Dedicated Citizen Resolution Verification Section & Status Display
    const citizenVerifContainer = document.getElementById('detail-citizen-verification-container');
    if (citizenVerifContainer) {
      let cvHtml = '';

      // If in CITIZEN_VERIFICATION state: show clear prompt (Step 10 Double Verification)
      if (g.status === 'CITIZEN_VERIFICATION') {
        const isComplainant = currentUser && (currentUser.id === g.citizen_id || currentUser.role === 'citizen');
        cvHtml += `
          <div class="card citizen-verification-banner" style="margin-top:1rem; border:2px solid #176B4D; background:#E8F3ED; border-radius:10px; padding:1.25rem; box-shadow:0 2px 6px rgba(22,163,74,0.18);">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.75rem;">
              <div style="flex:1; min-width:260px;">
                <div style="font-weight:800; color:#14532D; font-size:1.1rem; display:flex; align-items:center; gap:0.4rem; margin-bottom:0.35rem;">
                  Citizen Resolution Verification Required
                </div>
                <div style="font-size:0.95rem; color:#10533C; font-weight:600; line-height:1.45;">
                  The worker has reported that the work is complete. Please confirm whether your original problem has actually been solved.
                </div>
              </div>
              <div>
                ${isComplainant ? `
                  <button onclick="closeModal('modal-grievance-detail'); if(typeof openCitizenVerificationModal==='function') { openCitizenVerificationModal(${g.id}, '${g.tracking_id}', '${escapeHtml(g.title)}'); } else { window.location.href='/citizen'; }" class="btn touch-btn" style="background:#176B4D; color:#fff; font-weight:700; border:none; padding:0.65rem 1.25rem;">
                    ✓ Verify Resolution Now
                  </button>
                ` : `
                  <span style="font-size:0.85rem; background:#E8F3ED; color:#176B4D; font-weight:700; padding:6px 12px; border-radius:6px; display:inline-block;">
                    Awaiting Citizen Verification
                  </span>
                `}
              </div>
            </div>
          </div>
        `;
      }

      // Display Persistent Citizen Verification History (Never overwrite previous attempts)
      if (g.citizen_verifications && g.citizen_verifications.length > 0) {
        cvHtml += `
          <div class="card" style="margin-top:1rem; border:1px solid #DCE4DE; background:#FAFCFF; border-radius:10px; padding:1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1.5px solid #DCE4DE; padding-bottom:0.5rem; margin-bottom:0.75rem;">
              <h4 style="font-size:0.95rem; color:#176B4D; font-weight:700; margin:0; display:flex; align-items:center; gap:0.35rem;">
                Citizen Resolution Verification History (${g.citizen_verifications.length})
              </h4>
            </div>
            <div style="display:flex; flex-direction:column; gap:0.6rem;">
              ${g.citizen_verifications.map(v => {
                const respColor = v.response === 'YES' ? '#176B4D' : (v.response === 'PARTIALLY' ? '#D97706' : (v.response === 'NO' ? '#DC2626' : '#5D6B63'));
                return `
                  <div style="background:#FFFFFF; border:1px solid #DCE4DE; border-radius:8px; padding:0.75rem 0.9rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                      <div style="display:flex; align-items:center; gap:0.5rem;">
                        <span style="font-weight:700; font-size:0.85rem; color:#202B26;">Attempt #${v.attempt_number || 1}</span>
                        <span style="background:${respColor}; color:#fff; font-size:0.75rem; font-weight:700; padding:2px 7px; border-radius:4px;">
                          ${v.response}
                        </span>
                        <span style="font-size:0.78rem; color:#5D6B63;">[Method: ${v.method || v.verification_method || 'PORTAL'}]</span>
                        <span style="font-size:0.75rem; background:#E8F3ED; color:#5D6B63; padding:2px 6px; border-radius:4px; font-weight:600;">
                          ${v.verification_status || 'RECORDED'}
                        </span>
                      </div>
                      <div style="font-size:0.75rem; color:#5D6B63;">
                        ${v.response_timestamp || v.created_at}
                      </div>
                    </div>
                    ${v.remarks ? `
                      <div style="font-size:0.82rem; color:#5D6B63; margin-top:0.35rem; font-style:italic; background:#F8F7F2; padding:0.4rem 0.6rem; border-radius:4px;">
                        "${escapeHtml(v.remarks)}"
                      </div>
                    ` : ''}
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        `;
      }

      // Display Phone / IVR Verification Requests & Attempts (Step 9)
      if (g.verification_attempts && g.verification_attempts.length > 0) {
        cvHtml += `
          <div class="card" style="margin-top:1rem; border:1px solid #BAE6FD; background:#F0F9FF; border-radius:10px; padding:1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1.5px solid #E0F2FE; padding-bottom:0.5rem; margin-bottom:0.75rem;">
              <h4 style="font-size:0.95rem; color:#176B68; font-weight:700; margin:0; display:flex; align-items:center; gap:0.35rem;">
                Telephony / IVR Verification Logs (${g.verification_attempts.length})
              </h4>
              <span style="font-size:0.72rem; background:#FEF3C7; color:#92400E; border:1px solid #F59E0B; padding:2px 7px; border-radius:10px; font-weight:700;">
                Development / Mock Verification
              </span>
            </div>
            <div style="display:flex; flex-direction:column; gap:0.6rem;">
              ${g.verification_attempts.map(va => {
                const outcomeColor = va.call_outcome === 'ANSWERED' ? '#176B4D' : (va.call_outcome === 'NO_ANSWER' || va.call_outcome === 'BUSY' ? '#D97706' : '#DC2626');
                const phoneDisplay = va.phone_number_ref || va.phone_ref || (va.contact_number && va.contact_number.length >= 4 ? '******' + va.contact_number.slice(-4) : '******');
                return `
                  <div style="background:#FFFFFF; border:1px solid #DCE4DE; border-radius:8px; padding:0.75rem 0.9rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                      <div style="display:flex; align-items:center; gap:0.5rem;">
                        <span style="font-weight:700; font-size:0.85rem; color:#202B26;">Attempt #${va.attempt_number || 1}</span>
                        <span style="background:${outcomeColor}; color:#fff; font-size:0.75rem; font-weight:700; padding:2px 7px; border-radius:4px;">
                          ${va.call_outcome}
                        </span>
                        ${va.citizen_response ? `
                          <span style="background:#E0E7FF; color:#3730A3; font-size:0.75rem; font-weight:700; padding:2px 6px; border-radius:4px;">
                            Response: ${va.citizen_response}
                          </span>
                        ` : ''}
                        <span style="font-size:0.75rem; color:#176B68; font-family:monospace; background:#E0F2FE; padding:2px 6px; border-radius:4px;">
                          ${escapeHtml(phoneDisplay)}
                        </span>
                        <span style="font-size:0.72rem; color:#5D6B63;">[Ref: ${escapeHtml(va.provider_ref || 'MOCK')}]</span>
                      </div>
                      <div style="font-size:0.75rem; color:#5D6B63;">
                        ${va.response_time || va.attempted_at || 'Recently'}
                      </div>
                    </div>
                    ${va.remarks ? `
                      <div style="font-size:0.82rem; color:#5D6B63; margin-top:0.35rem; font-style:italic; background:#F8F7F2; padding:0.4rem 0.6rem; border-radius:4px;">
                        "${escapeHtml(va.remarks)}"
                      </div>
                    ` : ''}
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        `;
      }

      citizenVerifContainer.innerHTML = cvHtml;
    }

    // Rework / Reopen / Escalation Alert display
    let reworkBanner = '';
    if (g.status === 'REWORK_REQUIRED') {
      const officerRework = (g.officer_verifications || []).find(v => v.decision === 'REWORK_REQUESTED');
      const citizenPartial = (g.citizen_verifications || []).find(v => v.response === 'PARTIALLY');
      let source = 'Supervising Officer';
      let reworkNotes = 'Please re-inspect the issue and resubmit resolution evidence.';
      if (citizenPartial) {
        source = 'Complainant Citizen (Partially Solved)';
        reworkNotes = citizenPartial.remarks || reworkNotes;
      } else if (officerRework) {
        source = 'Supervising Officer';
        reworkNotes = officerRework.remarks || reworkNotes;
      }
      reworkBanner = `
        <div style="background:#FEF2F2; border:1px solid #F87171; border-radius:8px; padding:0.85rem 1rem; margin-top:1rem;">
          <div style="font-weight:700; color:#DC2626; font-size:0.88rem;">Rework Requested by ${source}:</div>
          <div style="color:#991B1B; font-size:0.85rem; margin-top:0.25rem;">"${escapeHtml(reworkNotes)}"</div>
        </div>
      `;
    } else if (g.status === 'REOPENED') {
      const citizenNo = (g.citizen_verifications || []).find(v => v.response === 'NO');
      const reopenNotes = citizenNo ? citizenNo.remarks : 'Citizen reported problem still exists.';
      reworkBanner = `
        <div style="background:#FFF1F2; border:1px solid #FDA4AF; border-radius:8px; padding:0.85rem 1rem; margin-top:1rem;">
          <div style="font-weight:700; color:#BE123C; font-size:0.88rem;">Grievance Reopened by Citizen (Problem Still Exists):</div>
          <div style="color:#9F1239; font-size:0.85rem; margin-top:0.25rem;">"${escapeHtml(reopenNotes)}"</div>
        </div>
      `;
    } else if (g.status === 'ESCALATED') {
      reworkBanner = `
        <div style="background:#FFF7ED; border:2px solid #EA580C; border-radius:8px; padding:0.85rem 1rem; margin-top:1rem;">
          <div style="font-weight:800; color:#C2410C; font-size:0.92rem; display:flex; align-items:center; gap:0.4rem;">
            Grievance ESCALATED to Senior Panchayat Oversight
          </div>
          <div style="color:#9A3412; font-size:0.85rem; margin-top:0.3rem;">
            This grievance has repeatedly failed verification inspections. It is now escalated for priority administrative review and field intervention.
          </div>
        </div>
      `;
    }

    const resNotesContainer = document.getElementById('detail-resolution-notes');
    if (resNotesContainer) {
      let resHtml = reworkBanner;
      if (g.resolution_notes) {
        resHtml += `
          <div style="background:#E8F3ED; border:1px solid #DCE4DE; border-radius:8px; padding:0.85rem 1rem; margin-top:1rem;">
            <div style="font-weight:700; color:#176B4D; font-size:0.88rem;">Official Resolution Notes:</div>
            <div style="color:#14532D; font-size:0.85rem; margin-top:0.25rem;">${escapeHtml(g.resolution_notes)}</div>
          </div>
        `;
      }
      resNotesContainer.innerHTML = resHtml;
    }

    const historyContainer = document.getElementById('detail-history-list');
    if (historyContainer && g.timeline) {
      historyContainer.innerHTML = g.timeline.map(item => `
        <div style="padding:0.75rem 0; border-bottom:1px solid #DCE4DE; display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <div style="font-weight:600; font-size:0.85rem; color:#202B26;">
              ${getStatusBadge(item.to_status)}
              <span style="font-size:0.8rem; color:#5D6B63; margin-left:0.5rem;">by ${escapeHtml(item.updated_by_name)} (${escapeHtml(item.updated_by_role)})</span>
            </div>
            <div style="font-size:0.82rem; color:#5D6B63; margin-top:0.35rem;">${escapeHtml(item.remarks)}</div>
          </div>
          <div style="font-size:0.75rem; color:#5D6B63; white-space:nowrap;">${item.created_at}</div>
        </div>
      `).join('');
    }

    const feedbackBox = document.getElementById('detail-feedback-box');
    if (feedbackBox) {
      if (g.feedback) {
        feedbackBox.innerHTML = `
          <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:8px; padding:0.85rem 1rem; margin-top:1rem;">
            <div style="font-weight:700; color:#92400E; font-size:0.85rem;">Citizen Feedback & Rating:</div>
            <div style="color:#F59E0B; font-size:1.1rem; margin:0.2rem 0;">${'★'.repeat(g.feedback.star_rating)}${'☆'.repeat(5 - g.feedback.star_rating)} (${escapeHtml(g.feedback.satisfaction)})</div>
            <div style="font-size:0.82rem; color:#78350F; font-style:italic;">"${escapeHtml(g.feedback.comments || 'No comment provided')}"</div>
          </div>
        `;
      } else if (g.status === 'RESOLVED' && currentUser && currentUser.role === 'citizen') {
        feedbackBox.innerHTML = `
          <div style="margin-top:1rem; text-align:center;">
            <button onclick="if(typeof openFeedbackModal==='function') openFeedbackModal(${g.id}, '${g.tracking_id}')" class="btn btn-accent btn-sm">Rate Resolution Experience</button>
          </div>
        `;
      } else {
        feedbackBox.innerHTML = '';
      }
    }

    openModal('modal-grievance-detail');
  } catch (err) {
    showToast('Error loading grievance details: ' + err.message, 'error');
  }
}

// Initial onload setup
document.addEventListener('DOMContentLoaded', () => {
  currentLang = window.currentLang || (typeof localStorage !== 'undefined' && localStorage.getItem('gramseva_lang')) || 'en';
  if (typeof window.applyTranslations === 'function') {
    window.applyTranslations(currentLang);
  }
  checkAuth();

  // Close modals on clicking backdrop
  document.querySelectorAll('.modal-backdrop').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.remove('active');
      }
    });
  });
});

