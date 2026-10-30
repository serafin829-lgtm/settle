const $ = s => document.querySelector(s); let CFG, SEL = null, CASES = [];
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const toast = t => { const e = $('#toast'); e.textContent = t; e.style.display = 'block'; setTimeout(() => e.style.display = 'none', 4500); };
const api = async (u, b) => { const r = await fetch(u, b ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) } : {}); const j = await r.json(); if (!r.ok) throw new Error(j.error || r.status); return j; };
const STATUS = { refunded: ['ok', 'Refunded'], pending_approval: ['wait', 'Awaiting your OK'], replied: ['grey', 'Replied'], blocked: ['bad', 'Blocked by guardrails'], rejected: ['grey', 'Rejected'], error: ['bad', 'PayPal error'] };
const pill = s => `<span class="pill ${(STATUS[s] || ['grey'])[0]}">${(STATUS[s] || [0, s])[1]}</span>`;
const money = v => (+v).toFixed(2) + ' ' + CFG.currency;
async function kpis() {
  const m = await api('/api/metrics');
  $('#kpis').innerHTML = [['Cases', m.cases], ['Refunded', money(m.refunded_total)], ['Resolved w/o human', m.resolved_without_human_pct + '%'], ['Awaiting you', m.awaiting], ['Blocked by guardrails', m.blocked]]
    .map(([k, v]) => `<div class="card kpi"><span class="muted small">${k}</span><b>${v}</b></div>`).join('');
}
let LASTSTATUS = null;
async function load(force) {
  CASES = await api('/api/cases'); kpis();
  if (CASES.length) $('#list').innerHTML = CASES.map(c => `<div class="case-item ${c.id === SEL ? 'sel' : ''}" data-id="${c.id}"><div class="row between"><b>#${c.id} · ${esc(c.order_ref || 'no order')}</b>${pill(c.status)}</div><div class="t muted">${esc(c.message.text)}</div></div>`).join('');
  document.querySelectorAll('.case-item').forEach(e => e.onclick = () => show(+e.dataset.id));
  const cur = CASES.find(x => x.id === SEL);
  if (!SEL && CASES.length) show(CASES[0].id);
  else if (cur && (cur.status !== LASTSTATUS || force)) show(SEL);
}
function traceHtml(t) {
  return t.map(s => `<div><span class="tool">→ ${esc(s.tool)}</span>(${esc(JSON.stringify(s.args || {}))})${s.result !== undefined ? `<br><span class="res">  ⇠ ${esc(JSON.stringify(s.result).slice(0, 420))}</span>` : ''}</div>`).join('');
}
function show(id) {
  SEL = id; const c = CASES.find(x => x.id === id); if (!c) return; LASTSTATUS = c.status;
  document.querySelectorAll('.case-item').forEach(e => e.classList.toggle('sel', +e.dataset.id === id));
  const p = c.proposal, o = c.order, isMoney = ['full_refund', 'partial_refund'].includes(p.action);
  $('#detail').innerHTML = `
  <div class="row between"><h2>Case #${c.id}</h2>${pill(c.status)}</div>
  <div class="small muted">From ${esc(c.message.email || 'unknown')} · engine: ${esc(c.engine)}</div>
  <h3>Customer message</h3><div class="msg">${esc(c.message.text)}</div>
  ${o ? `<h3>PayPal order</h3><div class="small">${esc(o.ref)} · PayPal order <code>${esc(o.paypal_order_id)}</code> · capture <code>${esc(o.capture_id)}</code><br>${o.items.map(i => esc(i.qty + ' × ' + i.name)).join(', ')} · paid <b>${money(o.amount)}</b> · refunded ${money(o.refunded)}</div>` : ''}
  <h3>Agent investigation</h3><div class="trace">${traceHtml(c.trace || [])}</div>
  <div class="card proposal" style="margin-top:14px">
    <div class="row between"><b>Proposal: ${esc(p.action.replace('_', ' '))}${isMoney ? ' · ' + money(p.amount) : ''}</b><span class="small muted">${esc(p.category)} · confidence ${(+p.confidence).toFixed(2)}</span></div>
    <div class="small" style="margin-top:6px">${esc(p.reasoning)}</div>
    <h3>Guardrails (enforced in code)</h3><ul class="checks small">${(c.checks || []).map(k => `<li>${k.ok ? '✅' : '⛔'} <b>${esc(k.check)}</b> — ${esc(k.detail)}</li>`).join('')}</ul>
    <label>Reply to customer (${esc(p.language || '')})</label><textarea id="reply">${esc(c.reply)}</textarea>
    ${c.status === 'pending_approval' ? `<div class="row" style="margin-top:10px"><input id="amt" type="number" step="0.01" value="${(+p.amount).toFixed(2)}" style="max-width:140px"><button class="ok" id="approve">Approve &amp; refund via PayPal</button><button class="bad" id="reject">Reject</button></div>` : ''}
    ${c.refund ? `<div class="small" style="margin-top:10px">${c.refund.error ? '⛔ ' + esc(c.refund.error) : `💸 PayPal refund <code>${esc(c.refund.id)}</code> · ${esc(c.refund.status)} · ${esc(c.refund.amount?.value)} ${esc(c.refund.amount?.currency_code)} · by ${esc(c.refund.by)}`}</div>` : ''}
    <div class="row" style="margin-top:10px"><button class="secondary small" id="rerun">Re-run agent</button></div>
  </div>`;
  const a = $('#approve'); if (a) a.onclick = async () => { a.disabled = true; try { await api(`/api/cases/${id}/approve`, { amount: +$('#amt').value, reply: $('#reply').value }); toast('Refund sent through PayPal ✔'); } catch (e) { toast(e.message); } load(); };
  const r = $('#reject'); if (r) r.onclick = async () => { await api(`/api/cases/${id}/reject`, {}); load(); };
  $('#rerun').onclick = async () => { try { const n = await api(`/api/cases/${id}/rerun`, {}); SEL = n.id; } catch (e) { toast(e.message); } load(true); };
}
async function init() {
  CFG = await api('/api/config');
  $('#mode').textContent = CFG.mock_paypal ? 'MOCK PayPal' : 'PayPal sandbox'; $('#mode').className = 'pill ' + (CFG.mock_paypal ? 'mock' : 'ok');
  $('#ai').textContent = 'AI: ' + CFG.ai_engine;
  if (!CFG.mock_paypal) $('#seed').style.display = 'none';
  const s = await api('/api/settings');
  $('#policy').value = s.policy; $('#lim').value = s.auto_approve_limit; $('#conf').value = s.min_confidence; $('#maxr').value = s.max_refunds_per_customer_30d; $('#auto').value = s.autopilot;
  $('#save').onclick = async () => { await api('/api/settings', { policy: $('#policy').value, auto_approve_limit: $('#lim').value, min_confidence: $('#conf').value, max_refunds_per_customer_30d: $('#maxr').value, autopilot: $('#auto').value }); toast('Saved'); };
  $('#seed').onclick = async () => { try { await api('/api/seed', {}); SEL = null; } catch (e) { toast(e.message); } load(true); };
  $('#refresh').onclick = () => load(true);
  load(); setInterval(load, 8000);
}
init();
