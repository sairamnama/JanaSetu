/**
 * GramSeva - Analytics & Reporting Chart.js Controller
 * Visualizes Category Breakdown, Ward Performance, and Resolution Metrics
 * All data sourced from real database records via /api/analytics
 */

let categoryChart = null;
let wardChart = null;
let statusChart = null;

document.addEventListener('DOMContentLoaded', async () => {
  await loadAnalyticsDashboard();
});

async function loadAnalyticsDashboard() {
  try {
    const res = await fetch('/api/analytics');
    const data = await res.json();
    if (!data.success) return;

    renderKPICards(data.summary);
    renderStatusBreakdown(data.summary);
    renderVerificationMetrics(data.verification);
    renderCategoryChart(data.by_category);
    renderWardChart(data.by_ward);
    renderStatusChart(data.summary);
    renderDeptPerformanceTable(data.dept_performance);
  } catch (err) {
    console.error('Error loading analytics:', err);
  }
}

function noData(v) { return v === null || v === undefined; }

function renderKPICards(summary) {
  const elTotal = document.getElementById('kpi-total');
  const elResolved = document.getElementById('kpi-resolved');
  const elAvgDays = document.getElementById('kpi-avg-days');
  const elRating = document.getElementById('kpi-rating');

  if (elTotal) elTotal.textContent = summary.total;
  if (elResolved) {
    const pct = summary.total > 0 ? Math.round((summary.resolved / summary.total) * 100) : 0;
    elResolved.textContent = `${summary.resolved} (${pct}%)`;
  }
  if (elAvgDays) {
    elAvgDays.textContent = noData(summary.avg_resolution_days)
      ? 'No data available'
      : `${summary.avg_resolution_days} Days`;
  }
  if (elRating) {
    elRating.textContent = noData(summary.avg_rating)
      ? 'No data available'
      : `${summary.avg_rating} / 5.0`;
  }
}

function renderStatusBreakdown(s) {
  const el = document.getElementById('status-breakdown-grid');
  if (!el) return;

  const items = [
    { label: window.t('status_submitted', 'Submitted'), value: s.submitted, color: '#5D6B63' },
    { label: window.t('status_under_review', 'Under Review'), value: s.under_review, color: '#176B68' },
    { label: window.t('status_in_progress', 'In Progress'), value: s.in_progress, color: '#D97706' },
    { label: window.t('status_work_completed', 'Work Completed'), value: s.work_completed, color: '#059669' },
    { label: window.t('status_officer_verification', 'Officer Verification'), value: s.officer_verification, color: '#7C3AED' },
    { label: window.t('status_citizen_verification', 'Citizen Verification'), value: s.citizen_verification, color: '#176B68' },
    { label: window.t('status_rework_required', 'Rework Required'), value: s.rework, color: '#DC2626' },
    { label: window.t('status_reopened', 'Reopened'), value: s.reopened, color: '#EA580C' },
    { label: window.t('status_escalated', 'Escalated'), value: s.escalated, color: '#BE123C' },
    { label: window.t('status_resolved', 'Resolved'), value: s.resolved, color: '#176B4D' },
    { label: window.t('status_rejected', 'Rejected'), value: s.rejected, color: '#78716C' },
  ];

  el.innerHTML = items.map(i => `
    <div style="background:#F8F7F2; border:1px solid #DCE4DE; border-left:4px solid ${i.color}; border-radius:6px; padding:0.6rem 0.8rem;">
      <div style="font-size:1.4rem; font-weight:800; color:${i.color};">${i.value}</div>
      <div style="font-size:0.75rem; font-weight:600; color:#5D6B63;">${i.label}</div>
    </div>
  `).join('');
}

function renderVerificationMetrics(v) {
  if (!v) return;
  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };
  set('vm-workers-completed', v.workers_marked_completed);
  set('vm-citizens-confirmed', v.citizens_confirmed_resolved);
  set('vm-failure-rate', noData(v.verification_failure_rate) ? '—' : v.verification_failure_rate + '%');
  set('vm-rework-rate', noData(v.rework_rate) ? '—' : v.rework_rate + '%');
}

function renderCategoryChart(categories) {
  const ctx = document.getElementById('categoryDoughnutChart');
  if (!ctx) return;

  const labels = categories.map(c => (window.getCategoryLabel ? window.getCategoryLabel(c.category) : c.category));
  const counts = categories.map(c => c.count);

  const brandColors = [
    '#176B4D', '#10B981', '#176B68', '#6366F1',
    '#F59E0B', '#EA580C', '#8B5CF6', '#5D6B63'
  ];

  if (categoryChart) categoryChart.destroy();

  categoryChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: counts,
        backgroundColor: brandColors.slice(0, labels.length),
        borderColor: '#FFFFFF',
        borderWidth: 2,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            boxWidth: 12,
            font: { family: 'Inter', size: 11, weight: '500' }
          }
        }
      },
      cutout: '65%'
    }
  });
}

function renderWardChart(wards) {
  const ctx = document.getElementById('wardBarChart');
  if (!ctx) return;

  const labels = wards.map(w => (window.currentLang === 'te' ? `వార్డు ${w.ward_number}` : `Ward ${w.ward_number}`));
  const totalCounts = wards.map(w => w.count);
  const resolvedCounts = wards.map(w => w.resolved_count || 0);

  if (wardChart) wardChart.destroy();

  wardChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: window.t('kpi_total_tickets', 'Total Complaints'),
          data: totalCounts,
          backgroundColor: '#176B4D',
          borderRadius: 6
        },
        {
          label: window.t('th_resolved', 'Resolved'),
          data: resolvedCounts,
          backgroundColor: '#10B981',
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1 }
        }
      },
      plugins: {
        legend: {
          position: 'top',
          labels: { font: { family: 'Inter', weight: '600' } }
        }
      }
    }
  });
}

function renderStatusChart(summary) {
  const ctx = document.getElementById('statusPieChart');
  if (!ctx) return;

  if (statusChart) statusChart.destroy();

  const isTe = (window.currentLang === 'te');
  const labels = isTe ? [
    'పరిశీలనలో ఉన్నవి',
    'పరిష్కార ప్రక్రియలో ఉన్నవి',
    'పని పూర్తయింది',
    'ధృవీకరణలో ఉన్నవి',
    'రీ-వర్క్ / పునఃప్రారంభం / ఎస్కలేషన్',
    'పరిష్కరించి మూసివేయబడినవి'
  ] : [
    'Pending Review',
    'In Remediation',
    'Work Completed',
    'Under Verification',
    'Rework / Reopened / Escalated',
    'Resolved & Closed'
  ];

  statusChart = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        data: [
          summary.submitted + summary.under_review,
          summary.assigned + summary.in_progress,
          summary.work_completed,
          (summary.officer_verification || 0) + (summary.citizen_verification || 0),
          summary.rework + summary.reopened + summary.escalated,
          summary.resolved
        ],
        backgroundColor: ['#38BDF8', '#F59E0B', '#059669', '#7C3AED', '#DC2626', '#10B981'],
        borderColor: '#FFFFFF',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { font: { family: 'Inter', size: 11 } }
        }
      }
    }
  });
}

function renderDeptPerformanceTable(departments) {
  const tbody = document.getElementById('dept-analytics-tbody');
  if (!tbody) return;

  tbody.innerHTML = departments.map(d => {
    const total = d.total_tickets || 0;
    const resolved = d.resolved_tickets || 0;
    const rate = total > 0 ? Math.round((resolved / total) * 100) : 100;

    return `
      <tr>
        <td style="font-weight:700; color:var(--text-main);">${d.name} (${d.code})</td>
        <td style="text-align:center; font-weight:600;">${total}</td>
        <td style="text-align:center; color:#D97706; font-weight:700;">${d.active_tickets || 0}</td>
        <td style="text-align:center; color:#176B4D; font-weight:700;">${resolved}</td>
        <td>
          <div style="display:flex; align-items:center; gap:0.5rem;">
            <div style="flex:1; background:#DCE4DE; height:8px; border-radius:4px; overflow:hidden;">
              <div style="width:${rate}%; background:#10B981; height:100%;"></div>
            </div>
            <span style="font-size:0.75rem; font-weight:700; color:#5D6B63; width:36px;">${rate}%</span>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

window.addEventListener('languageChanged', () => {
  loadAnalyticsDashboard();
});
