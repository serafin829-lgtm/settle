const $ = s => document.querySelector(s); const cart = {}; let CFG, last = null;
const toast = t => { const e = $('#toast'); e.textContent = t; e.style.display = 'block'; setTimeout(() => e.style.display = 'none', 4000); };
const api = async (u, b) => { const r = await fetch(u, b ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) } : {}); const j = await r.json(); if (!r.ok) throw new Error(j.error || r.status); return j; };
function render() {
  let tot = 0; const lines = [];
  for (const p of CFG.products) if (cart[p.sku]) { tot += p.price * cart[p.sku]; lines.push(`${cart[p.sku]} × ${p.name} — ${(p.price * cart[p.sku]).toFixed(2)}`); }
  $('#cartlines').innerHTML = lines.join('<br>') || 'Add something above.'; $('#total').textContent = tot.toFixed(2) + ' ' + CFG.currency;
}
function paid(r) { last = r; $('#after').style.display = 'block'; $('#oref').textContent = r.ref; $('#cemail').value = r.email || ''; $('#after').scrollIntoView({ behavior: 'smooth' }); for (const k in cart) delete cart[k]; render(); }
async function init() {
  CFG = await api('/api/config');
  $('#mode').textContent = CFG.mock_paypal ? 'MOCK PayPal (add sandbox keys to go live-sandbox)' : 'PayPal sandbox';
  $('#mode').className = 'pill ' + (CFG.mock_paypal ? 'mock' : 'ok');
  $('#products').innerHTML = CFG.products.map(p => `<div class="card product"><div class="art">${p.emoji}</div><b>${p.name}</b><div class="row between"><span>${p.price.toFixed(2)} ${CFG.currency}</span><button data-sku="${p.sku}">Add</button></div></div>`).join('');
  document.querySelectorAll('[data-sku]').forEach(b => b.onclick = () => { cart[b.dataset.sku] = (cart[b.dataset.sku] || 0) + 1; render(); });
  render();
  if (CFG.mock_paypal) {
    $('#mockpay').style.display = 'block';
    $('#mockbtn').onclick = async () => {
      try { const o = await api('/api/orders', { cart }); const r = await api(`/api/orders/${o.id}/capture`, { payer: { name: $('#mname').value, email: $('#memail').value } }); paid(r); }
      catch (e) { toast(e.message); }
    };
  } else {
    const s = document.createElement('script');
    s.src = `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(CFG.paypal_client_id)}&currency=${CFG.currency}&intent=capture`;
    s.onload = () => paypal.Buttons({
      createOrder: async () => (await api('/api/orders', { cart })).id,
      onApprove: async d => paid(await api(`/api/orders/${d.orderID}/capture`, {})),
      onError: e => toast('PayPal: ' + e)
    }).render('#paypal-buttons');
    document.head.appendChild(s);
  }
  $('#send').onclick = async () => {
    $('#send').disabled = true; $('#send').textContent = 'Settle is investigating…';
    try { const r = await api('/api/messages', { email: $('#cemail').value, order_ref: last && last.ref, text: $('#ctext').value });
      $('#reply').style.display = 'block'; $('#reply').textContent = r.status === 'pending_approval' ? '⏳ Thanks! Your case is ready and the shop owner is confirming the refund now — you will get an email from PayPal as soon as it is sent.' : r.status === 'blocked' ? 'Thanks, a member of the team will review your message today.' : r.reply; }
    catch (e) { toast(e.message); }
    $('#send').disabled = false; $('#send').textContent = 'Send to Taller Luna';
  };
}
init();
