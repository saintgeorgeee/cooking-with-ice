'use strict';
const $ = (selector) => document.querySelector(selector);
const token = $('meta[name="controller-token"]').content;
let activities = {}, status = {}, managing = false, editing = null;
let signature = '', toastTimer, lastPhase = '', offline = false;
const types = {playing: 'Playing', listening: 'Listening', watching: 'Watching', competing: 'Competing'};

async function api(path, method = 'GET', data) {
  const response = await fetch(path, {
    method, cache: 'no-store', signal: AbortSignal.timeout(10000),
    headers: {'Content-Type': 'application/json', 'X-Controller-Token': token},
    body: data === undefined ? undefined : JSON.stringify(data)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed.');
  return result;
}
function toast(message) {
  clearTimeout(toastTimer);
  $('#toast').textContent = message; $('#toast').hidden = false;
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 5000);
}
function element(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}
function artwork(activity, container, isCard = false) {
  const fallback = () => {
    container.replaceChildren(element('span', 'placeholder', activity.icon || '✦'));
  };
  const imageUrl = activity.preview ? '/' + activity.preview : activity.large_image;
  if (!imageUrl) { fallback(); return; }
  const img = element('img');
  img.alt = ''; img.src = imageUrl;
  if (isCard) img.loading = 'lazy';
  img.addEventListener('error', fallback, {once: true});
  container.append(img);
  if (isCard && /\.webp$/i.test(activity.preview)) container.classList.add('webp');
}
function renderCards(force = false) {
  const next = JSON.stringify([status.active_id, status.selected_id, status.phase, managing]);
  if (!force && signature === next) return;
  signature = next;
  const focused = document.activeElement?.dataset?.activity;
  const grid = $('#activities'); grid.replaceChildren();
  grid.classList.toggle('manage-mode', managing);
  $('#activity-count').textContent = Object.keys(activities).length;
  $('#empty').hidden = Object.keys(activities).length > 0;
  $('#add').hidden = !managing;
  $('#selection-note').hidden = managing;
  $('#manage').setAttribute('aria-pressed', String(managing));
  $('#grid-hint').textContent = managing ? 'Edit or add an activity.' : 'Choose an activity for Discord.';
  for (const [id, activity] of Object.entries(activities)) {
    const selected = status.selected_id === id, active = status.active_id === id;
    const card = element('article', 'activity-card' + (selected ? ' selected' : '') + (active ? ' confirmed' : ''));
    const button = element('button', 'card-main');
    button.type = 'button'; button.dataset.activity = id;
    button.setAttribute('aria-pressed', String(selected));
    button.setAttribute('aria-label', `${managing ? 'Edit' : 'Activate'} ${activity.label}${!activity.application_id ? ' · needs setup' : ''}`);
    const image = element('div', 'card-image'); artwork(activity, image, true);
    const body = element('div', 'card-body');
    const label = element('div', 'card-label');
    label.append(element('span', 'card-icon', activity.icon || '✦'), element('span', '', activity.label));
    const meta = element('div', 'card-meta');
    const state = element('span', 'card-status');
    state.append(element('span', 'dot'), element('span', '', active ? 'Active' : selected ? 'Waiting' : activity.application_id ? 'Ready' : 'Needs setup'));
    meta.append(state, element('span', 'card-timer', activity.timer ? '◷' : ''));
    meta.hidden = !active && !selected && !!activity.application_id && !activity.timer;
    body.append(label, meta); button.append(image, body); card.append(button);
    if (selected) card.append(element('span', 'live-marker', active ? '✓' : '·'));
    button.addEventListener('click', () => managing || !activity.application_id ? openEditor(id) : activate(id));
    if (managing) {
      const edit = element('button', 'card-edit', '✎');
      edit.setAttribute('aria-label', `Edit ${activity.label}`);
      edit.addEventListener('click', () => openEditor(id)); card.append(edit);
    }
    grid.append(card);
  }
  if (focused) [...grid.querySelectorAll('.card-main')].find(el => el.dataset.activity === focused)?.focus({preventScroll: true});
}
function clock() {
  const activity = activities[status.selected_id];
  if (!activity) return;
  if (!activity.timer) { $('#elapsed').hidden = true; return; }
  $('#elapsed').hidden = false;
  const elapsed = Math.max(0, Math.floor(Date.now() / 1000 - status.started_at));
  const h = Math.floor(elapsed / 3600), m = Math.floor(elapsed / 60) % 60, s = elapsed % 60;
  $('#elapsed').textContent = `Elapsed · ${[h,m,s].map(n => String(n).padStart(2,'0')).join(':')}${status.phase === 'active' ? '' : ' · waiting for Discord'}`;
}
function renderStatus(next) {
  status = next; offline = false;
  const activity = activities[status.selected_id];
  const active = status.phase === 'active';
  const stopping = status.phase === 'stopping';
  const badge = $('#presence-badge');
  badge.hidden = !activity && !stopping;
  badge.textContent = active ? '● ACTIVE' : activity ? (status.phase === 'connecting' ? '◌ CONNECTING' : '○ WAITING') : stopping ? '◌ STOPPING' : 'OFF';
  badge.className = 'pill' + (active ? ' active' : activity ? ' waiting' : '');
  $('#current-title').textContent = activity?.label || 'No activity';
  $('.current-panel').classList.toggle('active', active);
  $('#turn-off').disabled = !status.selected_id && !stopping;
  $('#rpc-error').hidden = !status.error;
  $('#rpc-error').textContent = status.error || '';
  if (!activity) $('#elapsed').hidden = true;
  const art = $('#current-art');
  const artKey = activity ? `${status.selected_id}:${activity.preview}:${activity.large_image}` : '';
  if (art.dataset.key !== artKey) {
    art.dataset.key = artKey; art.replaceChildren();
    if (activity) artwork(activity, art); else art.textContent = '◈';
  }
  const connection = $('#connection');
  connection.className = 'connection' + (status.connected ? ' connected' : status.discord_available ? ' available' : '');
  connection.lastElementChild.textContent = status.connected ? 'Discord · Connected' : 'Discord · Disconnected';
  if (active && lastPhase !== `${status.generation}:active`) toast(`${activity?.label} is active on Discord.`);
  lastPhase = `${status.generation}:${status.phase}`;
  clock(); renderCards();
}
async function activate(id) {
  try { renderStatus(await api(`/api/activity/${encodeURIComponent(id)}/activate`, 'POST')); }
  catch (error) { toast(error.message); }
}
$('#turn-off').addEventListener('click', async () => {
  try { renderStatus(await api('/api/deactivate', 'POST')); }
  catch (error) { toast(error.message); }
});
$('#manage').addEventListener('click', () => { managing = !managing; renderCards(true); });
$('#add').addEventListener('click', () => openEditor(null));
function openEditor(id) {
  editing = id;
  const form = $('#edit-form'); form.reset();
  for (const detail of form.querySelectorAll('details')) detail.open = false;
  const activity = activities[id] || {type:'playing', timer:false, icon:'✦'};
  for (const [key, value] of Object.entries(activity)) {
    const field = form.elements.namedItem(key);
    if (!field) continue;
    if (field.type === 'checkbox') field.checked = !!value; else field.value = value || '';
  }
  (activity.buttons || []).forEach((button, index) => {
    form.elements.namedItem(`button${index+1}_label`).value = button.label;
    form.elements.namedItem(`button${index+1}_url`).value = button.url;
  });
  $('#editor-title').textContent = id ? 'Edit activity' : 'New activity';
  $('#delete').hidden = !id; $('#form-error').hidden = true;
  $('#editor').showModal();
}
for (const id of ['close-editor', 'cancel']) $('#'+id).addEventListener('click', () => $('#editor').close());
$('#edit-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = event.currentTarget, data = {};
  for (const key of ['label','application_id','type','details','state','large_image','large_text','small_image','small_text','preview','icon']) data[key] = form.elements.namedItem(key)?.value.trim() || (key === 'preview' ? activities[editing]?.preview || null : null);
  data.timer = form.elements.namedItem('timer').checked;
  data.buttons = [];
  for (const index of [1,2]) {
    const label = form.elements.namedItem(`button${index}_label`).value.trim();
    const url = form.elements.namedItem(`button${index}_url`).value.trim();
    if (label || url) data.buttons.push({label, url});
  }
  $('#save').disabled = true;
  try {
    await api(editing ? `/api/activities/${encodeURIComponent(editing)}` : '/api/activities', editing ? 'PUT' : 'POST', data);
    await refreshActivities(); $('#editor').close(); toast('Activity saved.');
  } catch(error) { $('#form-error').textContent = error.message; $('#form-error').hidden = false; }
  finally { $('#save').disabled = false; }
});
$('#delete').addEventListener('click', () => $('#confirm-delete').showModal());
$('#confirm-delete').addEventListener('close', async () => {
  if ($('#confirm-delete').returnValue !== 'delete') return;
  try {
    await api(`/api/activities/${encodeURIComponent(editing)}`, 'DELETE');
    await refreshActivities(); $('#editor').close(); toast('Activity deleted.');
  } catch(error) { $('#form-error').textContent = error.message; $('#form-error').hidden = false; }
});
async function refreshActivities() {
  activities = await api('/api/activities'); signature = '';
  renderStatus(await api('/api/status')); renderCards(true);
}
async function poll() {
  try { renderStatus(await api('/api/status')); }
  catch {
    offline = true;
    $('#connection').className = 'connection';
    $('#connection').lastElementChild.textContent = 'Local server unavailable · Restart the app';
    $('#presence-badge').textContent = '○ UNVERIFIED';
    $('#presence-badge').className = 'pill waiting';
    $('.current-panel').classList.remove('active');
    $('#elapsed').hidden = false;
    $('#elapsed').textContent = 'Connection to the app was lost.';
  }
  setTimeout(poll, 2000);
}
async function boot() {
  try { await refreshActivities(); }
  catch (error) { toast('Could not load activities: ' + error.message); setTimeout(boot, 5000); return; }
  poll();
}
setInterval(() => { if (!offline) clock(); }, 1000);
boot();
