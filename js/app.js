// ═══════════════════════════════════════════
// CONFIG — Backend URL
// ═══════════════════════════════════════════
const API = 'http://localhost:8000';

// ═══════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════
let currentUser = null;
let selectedRole = 'operator';
let unreadCount = 0;
let PREDICTIONS = [];
let MESSAGES = [];

// ═══════════════════════════════════════════
// LOGIN
// ═══════════════════════════════════════════
function selectRole(btn) {
  document.querySelectorAll('.role-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  selectedRole = btn.dataset.role;
}

async function handleLogin() {
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-error');

  if (!email || !password) {
    errEl.textContent = 'Please enter email and password.';
    errEl.style.display = 'block';
    return;
  }

  errEl.style.display = 'none';
  document.getElementById('login-btn-text').style.display = 'none';
  document.getElementById('login-spinner').style.display = 'inline-block';

  try {
    // ── REAL API CALL to /login ──
    const response = await fetch(`${API}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (!response.ok) {
      // Login failed — show error from backend
      errEl.textContent = data.detail || 'Invalid email or password';
      errEl.style.display = 'block';
      return;
    }

    // Login success — save user info and token
    currentUser = {
      email: email,
      name: data.name,
      role: data.role,
      token: data.token
    };

    launchApp();

  } catch (err) {
    // Backend not reachable
    errEl.textContent = 'Cannot connect to backend. Make sure python main.py is running.';
    errEl.style.display = 'block';
  } finally {
    document.getElementById('login-btn-text').style.display = 'inline';
    document.getElementById('login-spinner').style.display = 'none';
  }
}

function launchApp() {
  document.getElementById('login-screen').classList.remove('active');
  document.getElementById('app-screen').classList.add('active');

  // Set user info in sidebar
  document.getElementById('user-name').textContent = currentUser.name;
  document.getElementById('user-role').textContent = currentUser.role;
  document.getElementById('user-avatar').textContent = currentUser.name[0].toUpperCase();
  document.getElementById('dash-username').textContent = currentUser.name;

  // Apply role permissions
  applyRolePermissions();

  // Load dashboard data
  drawDissolutionChart();
  drawEnergyChart();
  refreshDashboard();

  // Load messages from backend
  fetchMessages();
}

function handleLogout() {
  currentUser = null;
  PREDICTIONS = [];
  MESSAGES = [];
  document.getElementById('app-screen').classList.remove('active');
  document.getElementById('login-screen').classList.add('active');
  document.getElementById('login-email').value = '';
  document.getElementById('login-password').value = '';
  document.getElementById('prediction-results').style.display = 'none';
}

// ═══════════════════════════════════════════
// ROLE PERMISSIONS
// ═══════════════════════════════════════════
function applyRolePermissions() {
  const role = currentUser.role;

  document.querySelectorAll('.manager-only').forEach(el => {
    el.style.display = role === 'manager' ? '' : 'none';
  });

  document.querySelectorAll('.engineer-only').forEach(el => {
    el.style.display = (role === 'engineer' || role === 'manager') ? '' : 'none';
  });

  const carbonBtn = document.querySelector('[data-page="carbon"]');
  if (carbonBtn) {
    carbonBtn.style.display = (role === 'engineer' || role === 'manager') ? 'flex' : 'none';
  }
}

// ═══════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════
function navigate(btn) {
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  const page = btn.dataset.page;
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');

  if (page === 'messages') {
    fetchMessages();
    markMessagesRead();
  }
  if (page === 'dashboard') {
    refreshDashboard();
  }
}

// ═══════════════════════════════════════════
// PREDICTION — calls real backend ML model
// ═══════════════════════════════════════════
async function runPrediction() {
  const gran      = parseFloat(document.getElementById('p-gran-time').value);
  const binder    = parseFloat(document.getElementById('p-binder').value);
  const dryTemp   = parseFloat(document.getElementById('p-dry-temp').value);
  const dryTime   = parseFloat(document.getElementById('p-dry-time').value);
  const compForce = parseFloat(document.getElementById('p-comp-force').value);
  const speed     = parseFloat(document.getElementById('p-machine-speed').value);
  const lubricant = parseFloat(document.getElementById('p-lubricant').value);
  const moisture  = parseFloat(document.getElementById('p-moisture').value);

  if ([gran, binder, dryTemp, dryTime, compForce, speed, lubricant, moisture].some(isNaN)) {
    showToast('⚠ Please fill in all fields before predicting');
    return;
  }

  // Show loading state on button
  const btn = document.querySelector('.predictor-form-card .btn-primary');
  const originalText = btn.innerHTML;
  btn.innerHTML = '<span class="spinner"></span> Predicting...';
  btn.disabled = true;

  try {
    // ── REAL API CALL to /predict ──
    const response = await fetch(`${API}/predict`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentUser.token}`
      },
      body: JSON.stringify({
        granulation_time:  gran,
        binder_amount:     binder,
        drying_temp:       dryTemp,
        drying_time:       dryTime,
        compression_force: compForce,
        machine_speed:     speed,
        lubricant_conc:    lubricant,
        moisture_content:  moisture
      })
    });

    if (!response.ok) {
      showToast('⚠ Prediction failed — backend error');
      return;
    }

    const result = await response.json();

    // Build passes object from backend response
    const passes = {
      dissolution: result.individual_results.dissolution.pass,
      hardness:    result.individual_results.hardness.pass,
      friability:  result.individual_results.friability.pass,
      uniformity:  result.individual_results.uniformity.pass,
    };

    const allPass = result.overall_pass;

    // Save to local predictions list for dashboard
    PREDICTIONS.unshift({
      id: 'Batch-' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      result: allPass ? 'PASS' : 'FAIL',
      dissolution: result.dissolution_rate,
    });

    // Render results on screen
    renderPredictionResults(result, passes, allPass);
    refreshDashboard();

    showToast(allPass
      ? '✅ Prediction complete — Batch PASSES all standards'
      : '⚠ Prediction complete — Batch FAILS some standards'
    );

  } catch (err) {
    showToast('⚠ Cannot reach backend. Is python main.py running?');
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

function renderPredictionResults(result, passes, allPass) {
  const resultsEl = document.getElementById('prediction-results');
  resultsEl.style.display = 'block';

  // Helper to render one metric box
  const metricHTML = (label, val, unit, pass, passLabel, failLabel) => `
    <div class="result-metric" style="border-top: 2px solid ${pass ? 'var(--green)' : 'var(--red)'}">
      <div class="rm-label">${label}</div>
      <div class="rm-val" style="color:${pass ? 'var(--green)' : 'var(--red)'}">
        ${val}<span style="font-size:13px;font-weight:400"> ${unit}</span>
      </div>
      <div class="rm-status ${pass ? 'rm-pass' : 'rm-fail'}">
        ${pass ? '✓ ' + passLabel : '✗ ' + failLabel}
      </div>
    </div>`;

  // vs Golden comparison rows
  const vsG = result.vs_golden;
  const vsGoldenHTML = vsG ? [
    { label: 'Dissolution', pred: result.dissolution_rate + '%',   golden: vsG.dissolution?.golden + '%', better: vsG.dissolution?.better },
    { label: 'Hardness',    pred: result.hardness + ' N',          golden: vsG.hardness?.golden + ' N',   better: vsG.hardness?.better },
    { label: 'Friability',  pred: result.friability + '%',         golden: vsG.friability?.golden + '%',  better: vsG.friability?.better },
    { label: 'Energy',      pred: result.energy_estimate + ' kWh', golden: vsG.energy?.golden,            better: vsG.energy?.better },
  ].map(r => `
    <div class="rvg-row">
      <span class="rvg-label">${r.label}</span>
      <span style="color:${r.better ? 'var(--green)' : 'var(--muted)'}">This: ${r.pred}</span>
      <span style="color:var(--gold)">Golden: ${r.golden}</span>
    </div>`).join('') : '';

  resultsEl.innerHTML = `
    <h3 class="card-title" style="margin-bottom:16px">Prediction Results</h3>

    <div class="result-verdict ${allPass ? 'verdict-pass' : 'verdict-fail'}">
      <div class="verdict-icon">${allPass ? '✅' : '⚠'}</div>
      <div>
        <div class="verdict-title" style="color:${allPass ? 'var(--green)' : 'var(--red)'}">
          ${allPass ? 'BATCH WILL PASS' : 'BATCH MAY FAIL'}
        </div>
        <div class="verdict-sub">
          ${allPass
            ? 'All quality standards met with these settings'
            : 'One or more quality standards not met — see recommendations'}
        </div>
      </div>
    </div>

    <div class="result-metrics">
      ${metricHTML('Dissolution Rate',    result.dissolution_rate,    '%', passes.dissolution, 'PASS ≥85%',     'FAIL ≥85%')}
      ${metricHTML('Hardness',            result.hardness,            'N', passes.hardness,    'PASS 80–130N',  'FAIL 80–130N')}
      ${metricHTML('Friability',          result.friability,          '%', passes.friability,  'PASS ≤1.0%',    'FAIL ≤1.0%')}
      ${metricHTML('Content Uniformity',  result.content_uniformity,  '%', passes.uniformity,  'PASS 95–105%',  'FAIL 95–105%')}
    </div>

    <div class="result-metric" style="margin-bottom:16px;border-top:2px solid rgba(152,216,200,0.4)">
      <div class="rm-label">Estimated Energy</div>
      <div class="rm-val" style="color:#98D8C8">
        ${result.energy_estimate}<span style="font-size:13px;font-weight:400"> kWh</span>
      </div>
      <div class="rm-status" style="color:rgba(255,255,255,0.4)">
        ≈ ${result.co2_estimate} kg CO₂e
      </div>
    </div>

    <div class="result-recommendations">
      <div class="rec-title">💡 Root Cause</div>
      <div class="rec-item"><span class="rec-dot">→</span>${result.root_cause}</div>
    </div>

    <div class="result-recommendations" style="margin-top:10px">
      <div class="rec-title">📋 Recommendations</div>
      ${result.recommendations.map(r =>
        `<div class="rec-item"><span class="rec-dot">→</span>${r}</div>`
      ).join('')}
    </div>

    ${vsGoldenHTML ? `
    <div class="result-vs-golden">
      <div class="rvg-title">vs Golden Signature (T056)</div>
      ${vsGoldenHTML}
    </div>` : ''}

    <div class="accept-reject-row">
      <button class="btn-accept" onclick="handleDecision('accepted', ${result.overall_pass}, ${result.dissolution_rate})">
        ✓ Accept & Proceed
      </button>
      <button class="btn-reject" onclick="handleDecision('rejected', ${result.overall_pass}, ${result.dissolution_rate})">
        ✕ Reject & Revise
      </button>
    </div>
  `;
}

async function handleDecision(decision, passed, dissolution) {
  if (decision === 'accepted') {
    showToast('✓ Decision recorded — Batch approved to proceed');

    // If batch was predicted to FAIL but operator accepted — auto alert to engineer
    if (!passed) {
      await sendMessageToBackend(
        currentUser.name,
        currentUser.role,
        'engineer',
        `⚠ Operator accepted a FAIL-predicted batch. Dissolution: ${dissolution}%. Manual review recommended.`,
        'urgent'
      );
      showToast('🚨 Alert sent to Engineer for review');
    }
  } else {
    showToast('✕ Decision recorded — Batch sent back for parameter revision');
  }
}

async function fillGoldenValues() {
  try {
    // ── REAL API CALL to /golden ──
    const response = await fetch(`${API}/golden`);
    const data = await response.json();

    if (data.inputs) {
      document.getElementById('p-gran-time').value     = data.inputs.Granulation_Time;
      document.getElementById('p-binder').value        = data.inputs.Binder_Amount;
      document.getElementById('p-dry-temp').value      = data.inputs.Drying_Temp;
      document.getElementById('p-dry-time').value      = data.inputs.Drying_Time;
      document.getElementById('p-comp-force').value    = data.inputs.Compression_Force;
      document.getElementById('p-machine-speed').value = data.inputs.Machine_Speed;
      document.getElementById('p-lubricant').value     = data.inputs.Lubricant_Conc;
      document.getElementById('p-moisture').value      = data.inputs.Moisture_Content;
      showToast('✦ Golden Signature values loaded from backend');
    }
  } catch (err) {
    showToast('⚠ Could not load golden values — using defaults');
    // Fallback to hardcoded golden values
    document.getElementById('p-gran-time').value     = 27;
    document.getElementById('p-binder').value        = 13.5;
    document.getElementById('p-dry-temp').value      = 42;
    document.getElementById('p-dry-time').value      = 48;
    document.getElementById('p-comp-force').value    = 4.5;
    document.getElementById('p-machine-speed').value = 280;
    document.getElementById('p-lubricant').value     = 2.8;
    document.getElementById('p-moisture').value      = 0.2;
  }
}

// ═══════════════════════════════════════════
// MESSAGES — calls real backend
// ═══════════════════════════════════════════
async function fetchMessages() {
  try {
    // ── REAL API CALL to GET /messages ──
    const response = await fetch(
      `${API}/messages?role=${currentUser.role}`,
      { headers: { 'Authorization': `Bearer ${currentUser.token}` } }
    );

    const data = await response.json();
    MESSAGES = data.messages || [];

    renderMessages();
    updateMsgBadge();

  } catch (err) {
    console.log('Could not fetch messages:', err);
  }
}

async function sendMessage() {
  const text     = document.getElementById('msg-text').value.trim();
  const to       = document.getElementById('msg-to').value;
  const priority = document.getElementById('msg-priority').value;

  if (!text) { showToast('⚠ Please type a message first'); return; }

  const success = await sendMessageToBackend(
    currentUser.name, currentUser.role, to, text, priority
  );

  if (success) {
    document.getElementById('msg-text').value = '';
    showToast('✉ Message sent');
    fetchMessages(); // Refresh messages from backend
  }
}

async function quickAlert(text) {
  const success = await sendMessageToBackend(
    currentUser.name, currentUser.role, 'all', text, 'urgent'
  );
  if (success) {
    showToast('🚨 Quick alert sent to all team');
    fetchMessages();
  }
}

async function sendMessageToBackend(senderName, senderRole, to, text, priority) {
  try {
    // ── REAL API CALL to POST /messages ──
    const response = await fetch(`${API}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentUser.token}`
      },
      body: JSON.stringify({
        sender_name: senderName,
        sender_role: senderRole,
        to:          to,
        text:        text,
        priority:    priority
      })
    });

    return response.ok;
  } catch (err) {
    showToast('⚠ Could not send message — backend not reachable');
    return false;
  }
}

function renderMessages() {
  const listEl = document.getElementById('messages-list');
  if (!listEl) return;

  if (MESSAGES.length === 0) {
    listEl.innerHTML = '<div class="msg-empty">No messages yet</div>';
  } else {
    listEl.innerHTML = MESSAGES.map(msg => {
      const isSent = msg.from_name === currentUser.name;
      const priorityTag = msg.priority !== 'normal'
        ? `<span class="msg-priority-tag msg-priority-${msg.priority}">
             ${msg.priority === 'urgent' ? '🚨 Urgent' : 'ℹ Info'}
           </span>`
        : '';
      const toLabel = msg.to_role === 'all'      ? '→ All'
                    : msg.to_role === 'engineer'  ? '→ Engineer'
                    : msg.to_role === 'manager'   ? '→ Manager'
                    : '';
      return `
        <div class="msg-bubble ${isSent ? 'sent' : 'received'}">
          <div class="msg-meta">
            <span class="msg-sender">${msg.from_name}</span>
            <span class="msg-time">${msg.time} ${toLabel}</span>
            ${priorityTag}
          </div>
          <div class="msg-text">${msg.text}</div>
        </div>`;
    }).join('');

    listEl.scrollTop = listEl.scrollHeight;
  }

  // Update recent messages on dashboard
  const recentEl = document.getElementById('recent-messages-dash');
  if (recentEl && MESSAGES.length > 0) {
    recentEl.innerHTML = MESSAGES.slice(0, 3).map(m => `
      <div class="recent-item">
        <div class="ri-top">
          <span class="ri-id">${m.from_name}</span>
          <span class="ri-time">${m.time}</span>
        </div>
        <div class="ri-result">
          ${m.text.substring(0, 60)}${m.text.length > 60 ? '...' : ''}
        </div>
      </div>`).join('');
  } else if (recentEl) {
    recentEl.innerHTML = '<p class="empty-state">No messages yet.</p>';
  }
}

function markMessagesRead() {
  unreadCount = 0;
  updateMsgBadge();
}

function updateMsgBadge() {
  const badge    = document.getElementById('msg-badge');
  const dashCount = document.getElementById('dash-msg-count');
  const count = MESSAGES.length;

  if (count > 0) {
    badge.style.display = 'inline-block';
    badge.textContent = count;
  } else {
    badge.style.display = 'none';
  }
  if (dashCount) dashCount.textContent = count;
}

// ═══════════════════════════════════════════
// CARBON TRACKER
// ═══════════════════════════════════════════
function updateCarbonLimit(val) {
  document.getElementById('carbon-slider-val').textContent = val + ' kg CO₂e';
  document.getElementById('carbon-target-display').textContent = val + ' kg';
}

// ═══════════════════════════════════════════
// DASHBOARD REFRESH
// ═══════════════════════════════════════════
function refreshDashboard() {
  const recentEl = document.getElementById('recent-predictions');
  if (!recentEl) return;

  if (PREDICTIONS.length === 0) {
    recentEl.innerHTML = '<p class="empty-state">No predictions yet.<br>Use Batch Predictor to get started.</p>';
    return;
  }

  recentEl.innerHTML = PREDICTIONS.slice(0, 5).map(p => `
    <div class="recent-item">
      <div class="ri-top">
        <span class="ri-id">${p.id}</span>
        <span class="ri-time">${p.time}</span>
        <span style="color:${p.result === 'PASS' ? 'var(--green)' : 'var(--red)'}; font-weight:600; font-size:11px">
          ${p.result}
        </span>
      </div>
      <div class="ri-result">Dissolution: ${p.dissolution}%</div>
    </div>`).join('');
}

// ═══════════════════════════════════════════
// CHARTS (unchanged — use local BATCH_DATA)
// ═══════════════════════════════════════════
function drawDissolutionChart() {
  const canvas = document.getElementById('dissolution-chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const data = BATCH_DATA.slice(0, 15);
  const vals = data.map(d => d.dissolution);
  const labels = data.map(d => d.id);

  canvas.width = canvas.offsetWidth || 600;
  canvas.height = 180;

  const W = canvas.width, H = canvas.height;
  const pad = { top: 20, right: 20, bottom: 30, left: 40 };
  const chartW = W - pad.left - pad.right;
  const chartH = H - pad.top - pad.bottom;
  const minVal = 80, maxVal = 102;

  ctx.clearRect(0, 0, W, H);

  ctx.strokeStyle = 'rgba(255,255,255,0.05)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (chartH / 4) * i;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,0.25)';
    ctx.font = '10px DM Sans';
    ctx.fillText(Math.round(maxVal - ((maxVal - minVal) / 4) * i) + '%', 2, y + 4);
  }

  const goldenY = pad.top + chartH * (1 - (99.9 - minVal) / (maxVal - minVal));
  ctx.strokeStyle = 'rgba(245,200,66,0.4)';
  ctx.lineWidth = 1;
  ctx.setLineDash([5, 3]);
  ctx.beginPath(); ctx.moveTo(pad.left, goldenY); ctx.lineTo(W - pad.right, goldenY); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = 'rgba(245,200,66,0.7)';
  ctx.font = '9px DM Sans';
  ctx.fillText('Golden 99.9%', W - pad.right - 60, goldenY - 4);

  const gradient = ctx.createLinearGradient(0, pad.top, 0, H - pad.bottom);
  gradient.addColorStop(0, 'rgba(45,212,191,0.25)');
  gradient.addColorStop(1, 'rgba(45,212,191,0)');

  ctx.beginPath();
  vals.forEach((val, i) => {
    const x = pad.left + (chartW / (vals.length - 1)) * i;
    const y = pad.top + chartH * (1 - (val - minVal) / (maxVal - minVal));
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.lineTo(pad.left + chartW, H - pad.bottom);
  ctx.lineTo(pad.left, H - pad.bottom);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  ctx.strokeStyle = '#2DD4BF';
  ctx.lineWidth = 2;
  ctx.beginPath();
  vals.forEach((val, i) => {
    const x = pad.left + (chartW / (vals.length - 1)) * i;
    const y = pad.top + chartH * (1 - (val - minVal) / (maxVal - minVal));
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();

  vals.forEach((val, i) => {
    const x = pad.left + (chartW / (vals.length - 1)) * i;
    const y = pad.top + chartH * (1 - (val - minVal) / (maxVal - minVal));
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#2DD4BF';
    ctx.fill();
    if (i % 3 === 0) {
      ctx.fillStyle = 'rgba(255,255,255,0.3)';
      ctx.font = '9px DM Sans';
      ctx.fillText(labels[i], x - 10, H - pad.bottom + 12);
    }
  });
}

function drawEnergyChart() {
  const canvas = document.getElementById('energy-chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  canvas.width = canvas.offsetWidth || 500;
  canvas.height = 200;

  const data = BATCH_DATA.slice(0, 14).map(d => ({
    id: d.id,
    compForce: d.compForce,
    energy: +(d.compForce * 0.85 + d.speed * 0.045 + d.dryTemp * 0.08 + d.dryTime * 0.12 + 2.5).toFixed(1)
  })).sort((a, b) => a.compForce - b.compForce);

  const W = canvas.width, H = canvas.height;
  const pad = { top: 20, right: 20, bottom: 40, left: 45 };
  const chartW = W - pad.left - pad.right;
  const chartH = H - pad.top - pad.bottom;

  ctx.clearRect(0, 0, W, H);

  const maxEnergy = Math.max(...data.map(d => d.energy));
  const barW = chartW / data.length - 4;

  data.forEach((d, i) => {
    const x = pad.left + i * (chartW / data.length) + 2;
    const barH = (d.energy / maxEnergy) * chartH;
    const y = pad.top + chartH - barH;
    const color = d.compForce <= 6 ? '#6EE7B7' : d.compForce <= 10 ? '#2DD4BF' : d.compForce <= 14 ? '#F5C842' : '#FF6B6B';
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect ? ctx.roundRect(x, y, barW, barH, [3, 3, 0, 0]) : ctx.rect(x, y, barW, barH);
    ctx.fill();
    if (i % 2 === 0) {
      ctx.fillStyle = 'rgba(255,255,255,0.25)';
      ctx.font = '9px DM Sans';
      ctx.fillText(d.id, x, H - pad.bottom + 12);
    }
  });

  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (chartH / 4) * i;
    const val = Math.round(maxEnergy - (maxEnergy / 4) * i);
    ctx.fillStyle = 'rgba(255,255,255,0.25)';
    ctx.font = '10px DM Sans';
    ctx.fillText(val, 2, y + 4);
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
  }

  ctx.fillStyle = 'rgba(255,255,255,0.3)';
  ctx.font = '10px DM Sans';
  ctx.fillText('Est. kWh', 2, pad.top);
}

// ═══════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════
function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3000);
}

// ═══════════════════════════════════════════
// KEYBOARD + RESIZE
// ═══════════════════════════════════════════
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && document.getElementById('login-screen').classList.contains('active')) {
    handleLogin();
  }
});

window.addEventListener('resize', () => {
  if (document.getElementById('page-dashboard').classList.contains('active')) {
    drawDissolutionChart();
  }
  if (document.getElementById('page-carbon').classList.contains('active')) {
    drawEnergyChart();
  }
});
// ═══════════════════════════════════════════
// AI TRAINING ASSISTANT CHATBOT
// ═══════════════════════════════════════════

async function askAI() {

  const input = document.getElementById("ai-question");
  const chat = document.getElementById("ai-messages");

  if (!input || !chat) return;

  const question = input.value.trim();
  if (!question) return;

  // show user message
  chat.innerHTML += `
    <div class="ai-user">${question}</div>
  `;

  input.value = "";

  try {

    const res = await fetch(`${API}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ question: question })
    });

    const data = await res.json();

    chat.innerHTML += `
      <div class="ai-bot">${data.answer}</div>
    `;

    chat.scrollTop = chat.scrollHeight;

  } catch (err) {

    chat.innerHTML += `
      <div class="ai-bot">⚠ AI assistant unavailable. Backend not running.</div>
    `;

  }
}