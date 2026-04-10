/* ============================================================
   BahiKhata — app.js
   All frontend logic: API calls, routing, DOM management
   ============================================================ */

'use strict';

const API = 'http://localhost:8000/api/v1';

// ─────────────────────────────────────────
// STATE
// ─────────────────────────────────────────
const state = {
  token: null,
  user: null,
  parties: [],
  currentParty: null,        // Party object being viewed in ledger
  editingPartyId: null,      // For party modal edit mode
  editingTxnId: null,        // For txn modal edit mode
};

// ─────────────────────────────────────────
// INIT
// ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Restore session
  const savedToken = localStorage.getItem('bk_token');
  const savedUser  = localStorage.getItem('bk_user');
  if (savedToken && savedUser) {
    state.token = savedToken;
    state.user  = JSON.parse(savedUser);
    showApp();
  } else {
    showAuth();
  }

  // Allow Enter key in auth inputs
  document.getElementById('login-password').addEventListener('keydown', e => {
    if (e.key === 'Enter') doLogin();
  });
  document.getElementById('signup-password').addEventListener('keydown', e => {
    if (e.key === 'Enter') doSignup();
  });

  // Allow Enter key in AI input
  document.getElementById('ai-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') sendAiCommand();
  });

  // Set today's date as default in transaction modal
  document.getElementById('tm-date').value = todayISO();
});

// ─────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────
function todayISO() {
  return new Date().toISOString().split('T')[0];
}

function fmtDate(isoStr) {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function fmtAmount(n) {
  const num = parseFloat(n) || 0;
  return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function balanceCls(n) {
  const num = parseFloat(n) || 0;
  if (num > 0) return 'balance-positive';
  if (num < 0) return 'balance-negative';
  return 'balance-zero';
}

function setLoading(btnId, loading, label = 'Save') {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = loading;
  btn.innerHTML = loading
    ? '<span class="spinner"></span>'
    : label;
}

// ─────────────────────────────────────────
// TOAST NOTIFICATIONS
// ─────────────────────────────────────────
function toast(msg, type = 'info', duration = 3000) {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), duration);
}

// ─────────────────────────────────────────
// CONFIRM DIALOG
// ─────────────────────────────────────────
function showConfirm(title, msg) {
  return new Promise(resolve => {
    const dialog = document.getElementById('confirm-dialog');
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-msg').textContent = msg;
    dialog.classList.remove('hidden');

    const cleanup = (result) => {
      dialog.classList.add('hidden');
      okBtn.replaceWith(okBtn.cloneNode(true));
      cancelBtn.replaceWith(cancelBtn.cloneNode(true));
      resolve(result);
    };

    const okBtn     = document.getElementById('confirm-ok');
    const cancelBtn = document.getElementById('confirm-cancel');

    document.getElementById('confirm-ok').addEventListener('click', () => cleanup(true),   { once: true });
    document.getElementById('confirm-cancel').addEventListener('click', () => cleanup(false), { once: true });
  });
}

// ─────────────────────────────────────────
// API WRAPPER
// ─────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }

  const res = await fetch(`${API}${path}`, { ...options, headers });

  // Auto-logout on 401
  if (res.status === 401) {
    toast('Session expired. Please login again.', 'error');
    doLogout();
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }

  // 204 No Content
  if (res.status === 204) return null;

  return res.json();
}

// ─────────────────────────────────────────
// AUTH FLOW
// ─────────────────────────────────────────
function switchAuthTab(tab) {
  ['login', 'signup'].forEach(t => {
    document.getElementById(`tab-${t}`).classList.toggle('active', t === tab);
    document.getElementById(`panel-${t}`).classList.toggle('active', t === tab);
  });
}

function showAuth() {
  document.getElementById('auth-screen').style.display = 'flex';
  document.getElementById('app-screen').classList.remove('visible');
}

function showApp() {
  document.getElementById('auth-screen').style.display = 'none';
  document.getElementById('app-screen').classList.add('visible');
  document.getElementById('user-email').textContent = state.user?.email || '';
  navigateTo('parties');
}

async function doLogin() {
  const email    = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;

  if (!email || !password) { toast('Please fill in all fields', 'error'); return; }

  setLoading('login-btn', true, 'Login');
  try {
    const data = await apiFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });

    state.token = data.access_token;
    state.user  = data.user;
    localStorage.setItem('bk_token', state.token);
    localStorage.setItem('bk_user',  JSON.stringify(state.user));
    toast('Logged in successfully', 'success');
    showApp();
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    setLoading('login-btn', false, 'Login');
  }
}

async function doSignup() {
  const full_name = document.getElementById('signup-name').value.trim();
  const email     = document.getElementById('signup-email').value.trim();
  const password  = document.getElementById('signup-password').value;

  if (!full_name || !email || !password) { toast('Please fill in all fields', 'error'); return; }
  if (password.length < 6)              { toast('Password must be at least 6 characters', 'error'); return; }

  setLoading('signup-btn', true, 'Create Account');
  try {
    const data = await apiFetch('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name })
    });

    // Handle email confirmation required case
    if (!data.access_token) {
      toast('Account created! Please check your email to confirm.', 'info', 6000);
      switchAuthTab('login');
      return;
    }

    state.token = data.access_token;
    state.user  = data.user;
    localStorage.setItem('bk_token', state.token);
    localStorage.setItem('bk_user',  JSON.stringify(state.user));
    toast('Account created!', 'success');
    showApp();
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    setLoading('signup-btn', false, 'Create Account');
  }
}

async function doLogout() {
  try {
    await apiFetch('/auth/logout', { method: 'POST' });
  } catch (_) {}
  state.token = null;
  state.user  = null;
  localStorage.removeItem('bk_token');
  localStorage.removeItem('bk_user');
  showAuth();
}

// ─────────────────────────────────────────
// NAVIGATION
// ─────────────────────────────────────────
function navigateTo(view) {
  // Update sidebar active state
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  const navEl = document.getElementById(`nav-${view}`);
  if (navEl) navEl.classList.add('active');

  // Show correct view
  document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));

  if (view === 'parties') {
    document.getElementById('parties-view').classList.add('active');
    loadParties();
  } else if (view === 'ledger') {
    document.getElementById('ledger-view').classList.add('active');
    // Sidebar stays on "parties" since ledger is a sub-view
    document.getElementById('nav-parties').classList.add('active');
    loadLedger();
  } else if (view === 'ai') {
    document.getElementById('ai-view').classList.add('active');
  }
}

// ─────────────────────────────────────────
// PARTIES
// ─────────────────────────────────────────
async function loadParties() {
  const tbody = document.getElementById('parties-tbody');
  tbody.innerHTML = '<tr class="loading-row"><td colspan="6"><span class="spinner-dark spinner" style="margin-right:8px"></span>Loading...</td></tr>';

  try {
    state.parties = await apiFetch('/parties/');
    renderPartiesTable();
  } catch (e) {
    tbody.innerHTML = `<tr class="loading-row"><td colspan="6" style="color:var(--danger)">${e.message}</td></tr>`;
  }
}

function renderPartiesTable() {
  const tbody = document.getElementById('parties-tbody');
  if (!state.parties.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6">
          <div class="empty-state">
            <div class="icon">👥</div>
            <p>No parties yet. Add your first customer or supplier.</p>
          </div>
        </td>
      </tr>`;
    return;
  }

  tbody.innerHTML = state.parties.map(p => {
    const typePill = p.party_type === 'CUSTOMER'
      ? `<span class="pill pill-customer">Customer</span>`
      : `<span class="pill pill-supplier">Supplier</span>`;

    const aliases = (p.aliases || []).join(', ') || '—';
    const balCls  = balanceCls(p.current_balance);
    const bal     = fmtAmount(p.current_balance);

    return `<tr>
      <td>
        <a href="#" onclick="viewLedger('${p.id}'); return false;" style="font-weight:600">${esc(p.name)}</a>
      </td>
      <td>${typePill}</td>
      <td>${esc(p.phone || '—')}</td>
      <td style="color:var(--text-muted);font-size:12px">${esc(aliases)}</td>
      <td class="${balCls}">${bal}</td>
      <td>
        <div class="td-actions">
          <button class="btn btn-secondary btn-sm" onclick="openPartyModal('${p.id}')">Edit</button>
          <button class="btn btn-danger btn-sm" onclick="deleteParty('${p.id}', '${esc(p.name)}')">Delete</button>
          <button class="btn btn-ghost btn-sm" onclick="viewLedger('${p.id}')">Ledger →</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

function openPartyModal(partyId = null) {
  state.editingPartyId = partyId;
  const modal = document.getElementById('party-modal-backdrop');
  const title = document.getElementById('party-modal-title');

  // Clear form
  document.getElementById('pm-name').value    = '';
  document.getElementById('pm-phone').value   = '';
  document.getElementById('pm-aliases').value = '';
  document.getElementById('pm-type').value    = 'CUSTOMER';

  if (partyId) {
    const party = state.parties.find(p => p.id === partyId);
    if (party) {
      title.textContent = 'Edit Party';
      document.getElementById('pm-name').value    = party.name;
      document.getElementById('pm-phone').value   = party.phone || '';
      document.getElementById('pm-aliases').value = (party.aliases || []).join(', ');
      document.getElementById('pm-type').value    = party.party_type;
    }
  } else {
    title.textContent = 'Add Party';
  }

  modal.classList.remove('hidden');
  document.getElementById('pm-name').focus();
}

function closePartyModal(event) {
  // If called from backdrop click, only close if the backdrop itself was clicked
  if (event && event.target !== document.getElementById('party-modal-backdrop')) return;
  document.getElementById('party-modal-backdrop').classList.add('hidden');
  state.editingPartyId = null;
}

async function saveParty() {
  const name    = document.getElementById('pm-name').value.trim();
  const phone   = document.getElementById('pm-phone').value.trim() || null;
  const type    = document.getElementById('pm-type').value;
  const aliases = document.getElementById('pm-aliases').value
    .split(',').map(s => s.trim()).filter(Boolean);

  if (!name) { toast('Name is required', 'error'); return; }

  const body = { name, party_type: type, phone, aliases };

  setLoading('party-modal-save-btn', true, 'Save');
  try {
    if (state.editingPartyId) {
      await apiFetch(`/parties/${state.editingPartyId}`, {
        method: 'PUT',
        body: JSON.stringify(body)
      });
      toast('Party updated', 'success');
    } else {
      await apiFetch('/parties/', { method: 'POST', body: JSON.stringify(body) });
      toast('Party created', 'success');
    }
    document.getElementById('party-modal-backdrop').classList.add('hidden');
    loadParties();
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    setLoading('party-modal-save-btn', false, 'Save');
  }
}

async function deleteParty(partyId, name) {
  const confirmed = await showConfirm(
    'Delete Party?',
    `Are you sure you want to delete "${name}"? All associated transactions will also be deleted.`
  );
  if (!confirmed) return;

  try {
    await apiFetch(`/parties/${partyId}`, { method: 'DELETE' });
    toast('Party deleted', 'success');
    loadParties();
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ─────────────────────────────────────────
// LEDGER
// ─────────────────────────────────────────
function viewLedger(partyId) {
  const party = state.parties.find(p => p.id === partyId);
  if (!party) return;
  state.currentParty = party;
  navigateTo('ledger');
}

async function loadLedger() {
  const party = state.currentParty;
  if (!party) return;

  document.getElementById('ledger-party-name').textContent = party.name;
  document.getElementById('ledger-party-type').textContent =
    party.party_type === 'CUSTOMER' ? 'Customer' : 'Supplier';

  // Balance card
  const bal    = parseFloat(party.current_balance) || 0;
  const balEl  = document.getElementById('balance-amount');
  balEl.textContent  = fmtAmount(bal);
  balEl.className    = `amount ${balanceCls(bal)}`;

  const tbody = document.getElementById('ledger-tbody');
  tbody.innerHTML = '<tr class="loading-row"><td colspan="8"><span class="spinner-dark spinner" style="margin-right:8px"></span>Loading...</td></tr>';

  try {
    const txns = await apiFetch(`/ledger/${party.id}`);
    renderLedgerTable(txns);
  } catch (e) {
    tbody.innerHTML = `<tr class="loading-row"><td colspan="8" style="color:var(--danger)">${e.message}</td></tr>`;
  }
}

function renderLedgerTable(txns) {
  const tbody = document.getElementById('ledger-tbody');
  if (!txns.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8">
          <div class="empty-state">
            <div class="icon">📋</div>
            <p>No transactions yet for this party.</p>
          </div>
        </td>
      </tr>`;
    return;
  }

  tbody.innerHTML = txns.map(t => {
    const typePill = t.transaction_type === 'GIVE'
      ? `<span class="pill pill-give">GIVE</span>`
      : `<span class="pill pill-got">GOT</span>`;
    return `<tr>
      <td>${fmtDate(t.transaction_date)}</td>
      <td>${typePill}</td>
      <td>${t.quantity} ${esc(t.unit)}</td>
      <td>${fmtAmount(t.rate_per_unit)}</td>
      <td style="font-weight:600">${fmtAmount(t.amount)}</td>
      <td style="color:var(--text-muted);font-size:12px">${esc(t.payment_mode)}</td>
      <td style="color:var(--text-muted)">${esc(t.description || '—')}</td>
      <td>
        <div class="td-actions">
          <button class="btn btn-secondary btn-sm" onclick="openTxnModal('${t.id}', ${JSON.stringify(t).replace(/"/g, '&quot;')})">Edit</button>
          <button class="btn btn-danger btn-sm" onclick="deleteTxn('${t.id}')">Delete</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

function openTxnModal(txnId = null, txn = null) {
  state.editingTxnId = txnId;
  const modal = document.getElementById('txn-modal-backdrop');
  const title = document.getElementById('txn-modal-title');

  // Reset to defaults
  document.getElementById('tm-type').value = 'GIVE';
  document.getElementById('tm-mode').value = 'NONE';
  document.getElementById('tm-qty').value  = '1';
  document.getElementById('tm-rate').value = '0';
  document.getElementById('tm-unit').value = 'kg';
  document.getElementById('tm-date').value = todayISO();
  document.getElementById('tm-desc').value = '';

  if (txnId && txn) {
    title.textContent = 'Edit Entry';
    document.getElementById('tm-type').value = txn.transaction_type;
    document.getElementById('tm-mode').value = txn.payment_mode || 'NONE';
    document.getElementById('tm-qty').value  = txn.quantity;
    document.getElementById('tm-rate').value = txn.rate_per_unit;
    document.getElementById('tm-unit').value = txn.unit || 'kg';
    document.getElementById('tm-date').value = txn.transaction_date
      ? txn.transaction_date.split('T')[0]
      : todayISO();
    document.getElementById('tm-desc').value = txn.description || '';
  } else {
    title.textContent = 'Add Ledger Entry';
  }

  modal.classList.remove('hidden');
}

function closeTxnModal(event) {
  if (event && event.target !== document.getElementById('txn-modal-backdrop')) return;
  document.getElementById('txn-modal-backdrop').classList.add('hidden');
  state.editingTxnId = null;
}

async function saveTxn() {
  const party = state.currentParty;
  if (!party) return;

  const type  = document.getElementById('tm-type').value;
  const mode  = document.getElementById('tm-mode').value;
  const qty   = parseFloat(document.getElementById('tm-qty').value)  || 0;
  const rate  = parseFloat(document.getElementById('tm-rate').value) || 0;
  const unit  = document.getElementById('tm-unit').value;
  const date  = document.getElementById('tm-date').value;
  const desc  = document.getElementById('tm-desc').value.trim() || null;

  if (!date) { toast('Date is required', 'error'); return; }

  const body = {
    party_id: party.id,
    transaction_type: type,
    payment_mode: mode,
    quantity: qty,
    rate_per_unit: rate,
    unit,
    transaction_date: `${date}T00:00:00`,
    description: desc,
  };

  setLoading('txn-modal-save-btn', true, 'Save Entry');
  try {
    if (state.editingTxnId) {
      await apiFetch(`/ledger/${state.editingTxnId}`, {
        method: 'PUT',
        body: JSON.stringify(body)
      });
      toast('Entry updated', 'success');
    } else {
      await apiFetch('/ledger/', { method: 'POST', body: JSON.stringify(body) });
      toast('Entry added', 'success');
    }
    document.getElementById('txn-modal-backdrop').classList.add('hidden');
    // Refresh party balance
    await refreshPartyBalance(party.id);
    loadLedger();
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    setLoading('txn-modal-save-btn', false, 'Save Entry');
  }
}

async function deleteTxn(txnId) {
  const confirmed = await showConfirm('Delete Entry?', 'This transaction will be permanently removed.');
  if (!confirmed) return;

  try {
    await apiFetch(`/ledger/${txnId}`, { method: 'DELETE' });
    toast('Entry deleted', 'success');
    await refreshPartyBalance(state.currentParty.id);
    loadLedger();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function refreshPartyBalance(partyId) {
  // Re-fetch parties to get updated balance
  try {
    state.parties = await apiFetch('/parties/');
    const updated = state.parties.find(p => p.id === partyId);
    if (updated) {
      state.currentParty = updated;
      // Update balance card if in ledger view
      const bal   = parseFloat(updated.current_balance) || 0;
      const balEl = document.getElementById('balance-amount');
      balEl.textContent = fmtAmount(bal);
      balEl.className   = `amount ${balanceCls(bal)}`;
    }
  } catch (_) {}
}

// ─────────────────────────────────────────
// AI ASSISTANT
// ─────────────────────────────────────────
function setAiInput(text) {
  document.getElementById('ai-input').value = text;
  document.getElementById('ai-input').focus();
}

async function sendAiCommand() {
  const input = document.getElementById('ai-input').value.trim();
  if (!input) { toast('Please type a command', 'error'); return; }

  const sendBtn       = document.getElementById('ai-send-btn');
  const responseArea  = document.getElementById('ai-response-area');
  const responseBody  = document.getElementById('ai-response-body');
  const traceContent  = document.getElementById('trace-content');
  const traceCount    = document.getElementById('trace-count');

  sendBtn.disabled    = true;
  sendBtn.innerHTML   = '<span class="spinner"></span>';
  responseArea.classList.add('hidden');

  try {
    const result = await apiFetch('/ai/command', {
      method: 'POST',
      body: JSON.stringify({ text: input })
    });

    // Show response
    responseBody.textContent = result.response || '(No response)';
    responseArea.classList.remove('hidden');

    // Build trace
    const trace = result.trace || [];
    traceCount.textContent = trace.length;
    traceContent.innerHTML = trace.length
      ? trace.map(item => renderTraceItem(item)).join('')
      : '<div style="color:var(--text-muted);font-size:12px">No tools were called.</div>';

    // Auto-close trace
    traceContent.classList.remove('open');
    document.getElementById('trace-arrow').textContent = '▼';

  } catch (e) {
    toast(e.message, 'error');
  } finally {
    sendBtn.disabled  = false;
    sendBtn.textContent = 'Send';
  }
}

function renderTraceItem(item) {
  if (item.type === 'tool_call') {
    const argsStr = JSON.stringify(item.args, null, 2);
    return `<div class="trace-item trace-call">
      <div class="trace-label">🔧 Tool Call: ${esc(item.tool)}</div>
      <pre style="margin:0;font-size:11px;white-space:pre-wrap;color:#cbd5e1">${esc(argsStr)}</pre>
    </div>`;
  } else if (item.type === 'tool_result') {
    let resultStr = item.result;
    try {
      resultStr = JSON.stringify(JSON.parse(item.result), null, 2);
    } catch (_) {}
    return `<div class="trace-item trace-result">
      <div class="trace-label">✅ Result: ${esc(item.tool || '')}</div>
      <pre style="margin:0;font-size:11px;white-space:pre-wrap;color:#86efac">${esc(resultStr)}</pre>
    </div>`;
  }
  return '';
}

function toggleTrace() {
  const content = document.getElementById('trace-content');
  const arrow   = document.getElementById('trace-arrow');
  content.classList.toggle('open');
  arrow.textContent = content.classList.contains('open') ? '▲' : '▼';
}

// ─────────────────────────────────────────
// XSS HELPER
// ─────────────────────────────────────────
function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&#34;')
    .replace(/'/g, '&#39;');
}
