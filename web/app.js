'use strict';

const input = document.querySelector('#transcript');
const count = document.querySelector('#count');
const extract = document.querySelector('#extract');
const message = document.querySelector('#message');
const results = document.querySelector('#results');
const sourceSection = document.querySelector('#evidence-section');
const sourceTurns = document.querySelector('#source-turns');
const engine = document.querySelector('#engine');

const example = `Patient: I stopped taking the tablets last month.
Doctor: Thank you for letting me know. We'll arrange a blood test.
Patient: Okay, what happens after that?
Doctor: We can book a follow-up next week to review the results.`;

let analyzedText = null;
function updateCount() { count.textContent = `${input.value.length.toLocaleString()} / 40,000 characters`; }
function invalidateResults() {
  if (analyzedText !== null && input.value !== analyzedText) {
    analyzedText = null; sourceSection.hidden = true; sourceTurns.replaceChildren(); results.replaceChildren();
    const empty = make('div', 'empty compact');
    empty.append(make('h3', '', 'Conversation changed'), make('p', '', 'Extract orders again to review evidence for the updated text.'));
    results.append(empty); message.textContent = 'The previous results were cleared.';
  }
}
input.addEventListener('input', () => { updateCount(); invalidateResults(); });
document.querySelector('#example').addEventListener('click', () => { input.value = example; updateCount(); invalidateResults(); input.focus(); });

function turnLines(text) {
  return text.split(/\r?\n/).filter(line => line.trim()).map((line, index) => {
    const match = line.trim().match(/^(?:(\d+)\s+)?(?:\[\s*(doctor|clinician|patient)\s*\]|(doctor|clinician|patient)\s*:)\s*(.+)$/i);
    return match ? { id: Number(match[1] || index + 1), speaker: match[2] || match[3], text: match[4] } : null;
  }).filter(Boolean);
}
function make(tag, className, text) { const el = document.createElement(tag); if (className) el.className = className; if (text !== undefined) el.textContent = text; return el; }
function renderTurns(turns) {
  sourceTurns.replaceChildren();
  for (const turn of turns) {
    const li = make('li', 'source-turn'); li.id = `turn-${turn.id}`; li.tabIndex = -1;
    li.append(make('span', 'turn-number', String(turn.id).padStart(2, '0')), make('span', 'speaker', turn.speaker.toUpperCase()), make('span', 'turn-text', turn.text));
    sourceTurns.append(li);
  }
  sourceSection.hidden = false;
}
function focusEvidence(id) {
  for (const item of sourceTurns.children) item.classList.remove('selected');
  const target = document.getElementById(`turn-${id}`);
  if (target) { target.classList.add('selected'); target.scrollIntoView({ behavior: 'smooth', block: 'center' }); target.focus({ preventScroll: true }); }
}
function renderOrders(data) {
  results.replaceChildren();
  if (!data.orders.length) {
    const empty = make('div', 'empty compact'); empty.append(make('h3', '', 'No orders found'), make('p', '', 'This result can miss orders. Review the full conversation.')); results.append(empty); return;
  }
  data.orders.forEach((order, index) => {
    const card = make('article', 'order');
    const head = make('div', 'order-head'); head.append(make('span', 'order-type', order.order_type.toUpperCase()), make('span', 'order-index', String(index + 1).padStart(2, '0')));
    card.append(head, make('h3', '', order.description));
    if (order.reason) card.append(make('p', 'order-reason', `Reason: ${order.reason}`));
    const links = make('div', 'evidence-links'); links.append(make('span', 'evidence-label', 'SOURCE TURNS'));
    if (!order.provenance.length) links.append(make('span', 'warning', 'No source linked'));
    for (const id of order.provenance) {
      const button = make('button', 'turn-link', `Turn ${id}`); button.type = 'button';
      if (!document.getElementById(`turn-${id}`)) { button.disabled = true; button.textContent += ' · unavailable'; }
      else button.addEventListener('click', () => focusEvidence(id));
      links.append(button);
    }
    card.append(links);
    if (order.evidence_status !== 'linked') card.append(make('p', 'warning', 'Evidence is missing or references an unavailable turn.'));
    const review = make('div', 'review-actions');
    const label = make('span', 'evidence-label', 'REVIEW');
    const accept = make('button', 'review-button', 'Accept');
    const flag = make('button', 'review-button', 'Flag for review');
    for (const button of [accept, flag]) { button.type = 'button'; button.setAttribute('aria-pressed', 'false'); }
    function select(chosen) {
      for (const button of [accept, flag]) button.setAttribute('aria-pressed', String(button === chosen));
    }
    accept.addEventListener('click', () => select(accept));
    flag.addEventListener('click', () => select(flag));
    review.append(label, accept, flag); card.append(review);
    results.append(card);
  });
}

extract.addEventListener('click', async () => {
  if (!input.value.trim()) { message.textContent = 'Enter a simulated conversation or load the example.'; input.focus(); return; }
  extract.disabled = true; extract.textContent = 'Extracting…'; message.textContent = '';
  const submitted = input.value;
  try {
    const response = await fetch('/api/v1/extract', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ transcript: submitted }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'The request could not be completed.');
    if (input.value !== submitted) { message.textContent = 'Conversation changed during extraction. Extract again.'; return; }
    engine.textContent = data.engine === 'rules-v1' ? 'RULE BASELINE' : 'LOCAL MODEL';
    analyzedText = submitted; renderTurns(turnLines(submitted)); renderOrders(data);
    message.textContent = `${data.orders.length} proposed ${data.orders.length === 1 ? 'order' : 'orders'} · Review every item.`;
  } catch (error) { message.textContent = error.message || 'The service is unavailable. Try again.'; }
  finally { extract.disabled = false; extract.innerHTML = 'Extract orders <span aria-hidden="true">→</span>'; }
});

fetch('/health/ready').then(response => response.json()).then(data => {
  engine.textContent = data.engine === 'rules-v1' ? 'RULE BASELINE' : 'LOCAL MODEL';
}).catch(() => { engine.textContent = 'ENGINE UNAVAILABLE'; });
