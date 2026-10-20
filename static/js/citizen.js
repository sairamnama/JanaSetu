/**
 * GramSeva - Citizen Portal Logic
 * Handles My Grievances, Submissions, Interactive Stepper, Feedback
 */

let myGrievancesData = [];
let selectedGrievanceForFeedback = null;
let selectedGrievanceForVerification = null;

document.addEventListener('DOMContentLoaded', async () => {
  const user = await checkAuth();
  if (!user) {
    // If not logged in, prompt or offer quick login
    showToast('Browsing in Citizen View mode. You can log in or use the demo switcher above.', 'warning');
  }
  loadCitizenDashboard();
  setupImagePreview();
});

async function loadCitizenDashboard() {
  await loadCitizenStats();
  await loadMyGrievances();
}

async function loadCitizenStats() {
  try {
    const res = await fetch('/api/grievances?scope=my');
    const data = await res.json();
    if (!data.success) return;

    const list = data.grievances;
    myGrievancesData = list;

    const total = list.length;
    const pending = list.filter(g => g.status === 'SUBMITTED' || g.status === 'UNDER_REVIEW' || g.status === 'OFFICER_VERIFICATION' || g.status === 'CITIZEN_VERIFICATION').length;
    const progress = list.filter(g => g.status === 'ASSIGNED' || g.status === 'IN_PROGRESS' || g.status === 'REWORK_REQUIRED').length;
    const resolved = list.filter(g => g.status === 'VERIFIED' || g.status === 'RESOLVED' || g.status === 'CLOSED').length;

    const elTotal = document.getElementById('citizen-stat-total');
    const elPending = document.getElementById('citizen-stat-pending');
    const elProgress = document.getElementById('citizen-stat-progress');
    const elResolved = document.getElementById('citizen-stat-resolved');

    if (elTotal) elTotal.textContent = total;
    if (elPending) elPending.textContent = pending;
    if (elProgress) elProgress.textContent = progress;
    if (elResolved) elResolved.textContent = resolved;

    // Render prominent verification alert banner if grievances are in CITIZEN_VERIFICATION
    const pendingVerificationGrievances = list.filter(g => g.status === 'CITIZEN_VERIFICATION');
    const alertsEl = document.getElementById('citizen-verification-alerts');
    if (alertsEl) {
      if (pendingVerificationGrievances.length > 0) {
        alertsEl.innerHTML = `
          <div class="card" style="border: 2px solid #16A34A; background: #F0FDF4; margin-bottom: 1.5rem; padding: 1.25rem; border-radius: 10px; box-shadow: 0 2px 6px rgba(22,163,74,0.18);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
              <div style="flex:1; min-width:260px;">
                <div style="font-weight:800; color:#14532D; font-size:1.1rem; display:flex; align-items:center; gap:0.5rem;">
                  <span>🏁</span> Citizen Resolution Verification Required (${pendingVerificationGrievances.length})
                </div>
                <div style="font-size:0.95rem; color:#166534; font-weight:600; margin-top:0.35rem; line-height:1.45;">
                  The worker has reported that the work is complete. Please confirm whether your original problem has actually been solved.
                </div>
              </div>
              <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                ${pendingVerificationGrievances.map(item => `
                  <button onclick="openCitizenVerificationModal(${item.id}, '${item.tracking_id}', '${escapeHtml(item.title)}')" class="btn touch-btn" style="background:#16A34A; color:#fff; font-weight:700; border:none; padding:0.65rem 1.2rem;">
                    ✓ Verify ${item.tracking_id}
                  </button>
                `).join('')}
              </div>
            </div>
          </div>
        `;
      } else {
        alertsEl.innerHTML = '';
      }
    }
  } catch (err) {
    console.error('Error loading stats:', err);
  }
}

async function loadMyGrievances() {
  const tableBody = document.getElementById('my-grievances-tbody');
  if (!tableBody) return;

  const statusFilter = document.getElementById('filter-status')?.value || 'ALL';
  const categoryFilter = document.getElementById('filter-category')?.value || 'ALL';
  const searchTerm = document.getElementById('search-grievance')?.value.toLowerCase().trim() || '';

  let filtered = myGrievancesData.filter(g => {
    if (statusFilter !== 'ALL' && g.status !== statusFilter) return false;
    if (categoryFilter !== 'ALL' && g.category !== categoryFilter) return false;
    if (searchTerm) {
      const match = g.title.toLowerCase().includes(searchTerm) ||
                    g.tracking_id.toLowerCase().includes(searchTerm) ||
                    g.description.toLowerCase().includes(searchTerm) ||
                    g.location_landmark.toLowerCase().includes(searchTerm);
      if (!match) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align:center; padding:2.5rem; color:#64748B;">
          <div style="font-size:2rem; margin-bottom:0.5rem;">📂</div>
          <div style="font-weight:600;">No Grievances Found</div>
          <p style="font-size:0.85rem; margin-top:0.25rem;">Submit your first grievance using the form above.</p>
        </td>
      </tr>
    `;
    return;
  }

  tableBody.innerHTML = filtered.map(g => {
    const feedbackAction = (g.status === 'RESOLVED' && !g.star_rating)
      ? `<button onclick="openFeedbackModal(${g.id}, '${g.tracking_id}')" class="btn btn-sm btn-accent">⭐ Rate Service</button>`
      : (g.star_rating ? `<span title="Rated ${g.star_rating} Stars" style="color:#F59E0B; font-weight:700;">⭐ ${g.star_rating}/5</span>` : '');

    const verifyAction = (g.status === 'CITIZEN_VERIFICATION')
      ? `<button onclick="openCitizenVerificationModal(${g.id}, '${g.tracking_id}', '${escapeHtml(g.title)}')" class="btn btn-sm" style="background:#16A34A; color:#fff; font-weight:700; border:none; padding:0.35rem 0.75rem;">✓ Confirm Solved</button>`
      : '';

    return `
      <tr>
        <td>
          <a href="javascript:void(0)" onclick="openGrievanceDetail('${g.tracking_id}')" class="tracking-link">${g.tracking_id}</a>
        </td>
        <td>
          <div style="font-weight:600; color:var(--text-main);">${escapeHtml(g.title)}</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(g.location_landmark)} (Ward ${g.ward_number})</div>
        </td>
        <td>
          <span class="category-pill">${getCategoryIcon(g.category)} ${g.category.split(' ')[0]}</span>
        </td>
        <td>${getPriorityBadge(g.priority)}</td>
        <td>${getStatusBadge(g.status)}</td>
        <td style="font-size:0.8rem; color:#64748B;">${g.created_at.split(' ')[0]}</td>
        <td>
          <div style="display:flex; gap:0.4rem; align-items:center;">
            <button onclick="openGrievanceDetail('${g.tracking_id}')" class="btn btn-sm btn-outline-primary">View Details</button>
            ${verifyAction}
            ${feedbackAction}
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// ==========================================
// SUBMIT GRIEVANCE FORM
// ==========================================
async function handleGrievanceSubmit(event) {
  event.preventDefault();
  const form = event.target;
  const submitBtn = form.querySelector('button[type="submit"]');

  if (!currentUser) {
    showToast('Please log in as a citizen to submit a grievance', 'warning');
    openLoginModal('login');
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = 'Submitting...';

  try {
    const formData = new FormData(form);
    const res = await fetch('/api/grievances', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();

    if (data.success) {
      showToast(data.message, 'success');
      form.reset();
      document.getElementById('image-preview-area').innerHTML = '';
      await loadCitizenDashboard();
      // Open detail modal directly to show the citizen their newly created grievance!
      setTimeout(() => openGrievanceDetail(data.tracking_id), 600);
    } else {
      showToast(data.error || 'Submission failed', 'error');
    }
  } catch (err) {
    showToast('Error submitting grievance: ' + err.message, 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Submit Grievance';
  }
}

function setupImagePreview() {
  const fileInput = document.getElementById('evidence_image');
  const previewArea = document.getElementById('image-preview-area');
  if (!fileInput || !previewArea) return;

  fileInput.addEventListener('change', (e) => {
    previewArea.innerHTML = '';
    const file = e.target.files[0];
    if (file) {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (re) => {
          previewArea.innerHTML = `
            <div style="margin-top:0.75rem; display:inline-block; position:relative; border-radius:8px; overflow:hidden; border:1px solid #CBD5E1;">
              <img src="${re.target.result}" style="max-height:120px; display:block; object-fit:cover;" />
              <div style="background:rgba(0,0,0,0.6); color:#fff; font-size:0.7rem; padding:2px 6px; text-align:center;">Selected Photo</div>
            </div>
          `;
        };
        reader.readAsDataURL(file);
      }
    }
  });
}

// Detail & Stepper handled globally in app.js


// ==========================================
// CITIZEN FEEDBACK & RATING MODAL
// ==========================================
let currentStarRating = 5;

function openFeedbackModal(grievanceId, trackingId) {
  selectedGrievanceForFeedback = grievanceId;
  currentStarRating = 5;
  document.getElementById('feedback-tracking-id').textContent = trackingId;
  updateStars(5);
  closeModal('modal-grievance-detail');
  openModal('modal-feedback');
}

function updateStars(num) {
  currentStarRating = num;
  const stars = document.querySelectorAll('#feedback-stars-container .star');
  stars.forEach((star, index) => {
    star.classList.toggle('filled', index < num);
  });
}

async function handleFeedbackSubmit(event) {
  event.preventDefault();
  if (!selectedGrievanceForFeedback) return;

  const satisfaction = document.querySelector('input[name="satisfaction"]:checked')?.value || 'Satisfied';
  const comments = document.getElementById('feedback-comments')?.value || '';

  try {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        grievance_id: selectedGrievanceForFeedback,
        star_rating: currentStarRating,
        satisfaction: satisfaction,
        comments: comments
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      closeModal('modal-feedback');
      await loadCitizenDashboard();
    } else {
      showToast(data.error, 'error');
    }
  } catch (err) {
    showToast('Failed to submit feedback: ' + err.message, 'error');
  }
}

// ==========================================
// STEP 6: CITIZEN RESOLUTION VERIFICATION
// ==========================================
async function openCitizenVerificationModal(grievanceId, trackingId, title) {
  selectedGrievanceForVerification = grievanceId;
  const modal = document.getElementById('modal-citizen-verify');
  if (!modal) return;

  document.getElementById('verify-modal-tracking-id').textContent = trackingId;
  document.getElementById('verify-modal-title').textContent = title || `Grievance #${grievanceId}`;
  document.getElementById('verify-modal-meta').textContent = 'Ananthapur Gram Panchayat • Awaiting Complainant Confirmation';
  
  const remarksInput = document.getElementById('citizen-verify-remarks');
  if (remarksInput) remarksInput.value = '';

  const proofBox = document.getElementById('verify-modal-proof');
  const proofText = document.getElementById('verify-modal-proof-text');
  const historyBox = document.getElementById('verify-modal-history');
  const historyList = document.getElementById('verify-modal-history-list');

  // Fetch full grievance details to preview worker resolution proof and previous verification history
  try {
    const res = await fetch(`/api/grievances/${grievanceId}`);
    const data = await res.json();
    if (data.success && data.grievance) {
      const g = data.grievance;
      if (g.title) {
        document.getElementById('verify-modal-title').textContent = g.title;
      }
      document.getElementById('verify-modal-meta').textContent = `Ward ${g.ward_number} • ${g.location_landmark} • ${g.category}`;

      // Worker proof preview
      if (proofBox && proofText) {
        if (g.resolution_proofs && g.resolution_proofs.length > 0) {
          const latestProof = g.resolution_proofs[0];
          proofText.textContent = `"${latestProof.completion_notes || latestProof.description || 'Work completed'}" — Submitted by ${latestProof.worker_name || 'Worker'} (${latestProof.created_at})`;
          proofBox.style.display = 'block';
        } else {
          proofBox.style.display = 'none';
        }
      }

      // Verification history (Step 6: Never overwrite previous attempts, display verification history)
      if (historyBox && historyList) {
        if (g.citizen_verifications && g.citizen_verifications.length > 0) {
          historyBox.style.display = 'block';
          historyList.innerHTML = g.citizen_verifications.map(v => `
            <div style="padding:0.6rem 0.8rem; border-bottom:1px solid #F1F5F9; font-size:0.8rem; display:flex; justify-content:space-between; align-items:center;">
              <div>
                <span style="font-weight:700; color:#1E293B;">Attempt #${v.attempt_number || 1}</span>
                <span style="background:#E2E8F0; padding:2px 6px; border-radius:4px; font-size:0.75rem; margin-left:4px; font-weight:600;">${v.response}</span>
                <span style="color:#64748B; margin-left:4px;">(${v.verification_status || v.method || 'PORTAL'})</span>
                ${v.remarks ? `<div style="color:#475569; font-style:italic; margin-top:2px;">"${escapeHtml(v.remarks)}"</div>` : ''}
              </div>
              <div style="color:#94A3B8; font-size:0.75rem; white-space:nowrap;">${v.response_timestamp || v.created_at}</div>
            </div>
          `).join('');
        } else {
          historyBox.style.display = 'none';
          historyList.innerHTML = '';
        }
      }
    }
  } catch (e) {
    console.error('Error fetching grievance for verification:', e);
  }

  closeModal('modal-grievance-detail');
  openModal('modal-citizen-verify');
}

async function submitCitizenVerification(response) {
  if (!selectedGrievanceForVerification) return;

  const remarks = document.getElementById('citizen-verify-remarks')?.value.trim() || '';
  const buttons = document.querySelectorAll('#modal-citizen-verify button');
  buttons.forEach(b => b.disabled = true);

  try {
    const res = await fetch(`/api/grievances/${selectedGrievanceForVerification}/citizen-verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        response: response,
        verification_method: 'PORTAL',
        remarks: remarks
      })
    });
    const data = await res.json();

    if (data.success) {
      if (response === 'YES') {
        showToast('✓ Verification confirmed: Problem completely solved! Thank you.', 'success');
      } else if (response === 'PARTIALLY') {
        showToast('◐ Verification recorded: Problem partially solved. Rework requested.', 'warning');
      } else if (response === 'NO') {
        showToast('✕ Verification recorded: Problem still exists. Status updated.', 'error');
      } else {
        showToast('? Status recorded: Unable to verify. Grievance remains pending verification.', 'info');
      }
      closeModal('modal-citizen-verify');
      await loadCitizenDashboard();
    } else {
      showToast(data.error || 'Verification submission failed.', 'error');
    }
  } catch (err) {
    showToast('Failed to submit verification: ' + err.message, 'error');
  } finally {
    buttons.forEach(b => b.disabled = false);
  }
}

function printReceipt() {
  window.print();
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
}
