const $ = (selector) => document.querySelector(selector);
const state = { projectId: null, project: null, pollTimer: null, monitoredJob: null, saveTimers: new Map(), pendingPassages: new Map() };

async function api(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { message = (await response.json()).detail || message; } catch {}
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2).toLowerCase(), value);
    else node.setAttribute(key, value);
  }
  for (const child of children) node.append(child);
  return node;
}

async function refreshHealth() {
  try {
    const health = await api('/api/health');
    const status = $('#service-status');
    status.classList.toggle('ready', health.text_model_configured);
    status.innerHTML = `<i></i>${health.text_model_configured ? 'Model Studio connected' : 'Add Model Studio API key'}`;
  } catch {}
}

async function loadProjects() {
  const projects = await api('/api/projects');
  const list = $('#project-list');
  list.replaceChildren();
  if (!projects.length) {
    list.append(el('div', { class: 'empty-state', text: 'Your projects will show up here after you upload a PDF.' }));
    return;
  }
  for (const project of projects) {
    const card = el('article', { class: 'project-card', onclick: () => openProject(project.id) });
    card.append(el('h3', { text: project.title }), el('p', { text: `${project.page_count || 'Processing'} pages · ${new Date(project.updated_at).toLocaleDateString()}` }), el('span', { class: 'status-pill', text: project.status }));
    list.append(card);
  }
}

$('#pdf-file').addEventListener('change', async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  $('#upload-message').textContent = 'Uploading and extracting text…';
  const form = new FormData(); form.append('file', file);
  try {
    const result = await api('/api/projects/upload', { method: 'POST', body: form });
    await openProject(result.project_id);
    monitorJob(result.job_id);
  } catch (error) { $('#upload-message').textContent = error.message; }
  event.target.value = '';
});

async function openProject(id) {
  state.projectId = id;
  $('#home-view').hidden = true; $('#project-view').hidden = false;
  await reloadProject();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function reloadProject() {
  const project = await api(`/api/projects/${state.projectId}`);
  state.project = project;
  $('#project-title').textContent = project.title;
  $('#project-meta').textContent = `${project.page_count} pages · ${project.passages.length} passages · ${project.source_name}`;
  renderPassages(project);
  renderSpeakers(project);
  renderJobs(project.jobs);
  const activeJob = project.jobs.find((job) => job.status === 'queued' || job.status === 'running');
  if (activeJob && state.monitoredJob !== activeJob.id) monitorJob(activeJob.id);
  const result = $('#audio-result');
  result.hidden = !project.audio_url;
  result.replaceChildren();
  if (project.audio_url) {
    result.append(el('strong', { text: 'Your audiobook is ready' }), el('audio', { class: 'speaker-audio', controls: '', src: project.audio_url }), el('a', { href: project.audio_url, download: 'audiobook.mp3', text: 'Download MP3' }));
  }
  $('#analyze-button').disabled = project.passages.length === 0;
  $('#generate-button').disabled = project.passages.length === 0;
}

function renderPassages(project) {
  const list = $('#passage-list'); list.replaceChildren();
  if (!project.passages.length) {
    list.append(el('div', { class: 'empty-state', text: 'Extracting text from your PDF. This can take a little while.' }));
    return;
  }
  for (const passage of project.passages) {
    const card = el('article', { class: 'passage-card' });
    const meta = el('div', { class: 'passage-meta' });
    meta.append(el('span', { text: `Page ${passage.page} · Passage ${passage.ordinal + 1}` }));
    const select = el('select', { 'aria-label': 'Speaker assignment' });
    select.append(el('option', { value: '', text: 'Choose speaker' }));
    for (const speaker of project.speakers) {
      const option = el('option', { value: speaker.id, text: speaker.name });
      if (speaker.id === passage.speaker_id) option.selected = true;
      select.append(option);
    }
    if (passage.confidence !== null && passage.confidence !== undefined) meta.append(el('span', { class: 'confidence', text: `${Math.round(passage.confidence * 100)}% match` }));
    meta.append(select);
    const textarea = el('textarea', { 'aria-label': `Text for page ${passage.page}`, text: passage.text });
    const save = () => queuePassageSave(passage.id, textarea.value, select.value, card);
    textarea.addEventListener('input', save); select.addEventListener('change', save);
    card.append(meta, textarea); list.append(card);
  }
}

function queuePassageSave(id, text, speakerId, card) {
  clearTimeout(state.saveTimers.get(id));
  state.pendingPassages.set(id, { text, speakerId, card });
  const timer = setTimeout(() => savePassage(id).catch((error) => showBanner(error.message, true)), 550);
  state.saveTimers.set(id, timer);
}

async function savePassage(id) {
  const pending = state.pendingPassages.get(id);
  if (!pending) return;
  state.pendingPassages.delete(id); state.saveTimers.delete(id);
  await api(`/api/projects/${state.projectId}/passages/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: pending.text, speaker_id: pending.speakerId || null }) });
  pending.card.classList.add('saved'); setTimeout(() => pending.card.classList.remove('saved'), 800);
}

async function flushPassageSaves() {
  const ids = [...state.pendingPassages.keys()];
  ids.forEach((id) => clearTimeout(state.saveTimers.get(id)));
  await Promise.all(ids.map(async (id) => {
    try { await savePassage(id); }
    catch (error) { showBanner(error.message, true); throw error; }
  }));
}

function renderSpeakers(project) {
  const list = $('#speaker-list'); list.replaceChildren();
  if (!project.speakers.length) {
    list.append(el('div', { class: 'empty-state', text: 'Run speaker analysis to find the narrator and characters.' }));
    return;
  }
  for (const speaker of project.speakers) {
    const card = el('div', { class: 'speaker-card' });
    const name = el('input', { value: speaker.name, maxlength: '100', 'aria-label': 'Speaker name' });
    const prompt = el('textarea', { maxlength: '2048', 'aria-label': `Voice description for ${speaker.name}`, placeholder: 'e.g. A calm, warm adult voice with measured pacing.' });
    prompt.value = speaker.voice_prompt || '';
    const save = el('button', { class: 'small-button', text: 'Save voice details' });
    const preview = el('button', { class: 'small-button', text: speaker.voice_id ? 'Create new preview' : 'Create voice preview' });
    const status = el('span', { class: 'muted', text: speaker.voice_id ? 'Voice ready' : 'Voice not created' });
    const actions = el('div', { class: 'speaker-actions' }, [preview, status]);
    save.addEventListener('click', async () => {
      try {
        await api(`/api/projects/${state.projectId}/speakers/${speaker.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: name.value, voice_prompt: prompt.value }) });
        showBanner('Speaker details saved.'); await reloadProject();
      } catch (error) { showBanner(error.message, true); }
    });
    preview.addEventListener('click', async () => {
      preview.disabled = true; preview.textContent = 'Creating…';
      try {
        await api(`/api/projects/${state.projectId}/speakers/${speaker.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: name.value, voice_prompt: prompt.value }) });
        await api(`/api/projects/${state.projectId}/speakers/${speaker.id}/preview`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
        await reloadProject();
      } catch (error) { showBanner(error.message, true); preview.disabled = false; preview.textContent = 'Retry preview'; }
    });
    card.append(el('div', { class: 'speaker-top' }, [name]), prompt, save, actions);
    if (speaker.has_preview) card.append(el('audio', { class: 'speaker-audio', controls: '', src: `/api/projects/${project.id}/speakers/${speaker.id}/preview` }));
    list.append(card);
  }
}

function showBanner(message, error = false) {
  const banner = $('#job-banner'); banner.hidden = false; banner.classList.toggle('error', error); banner.textContent = message;
}

function renderJobs(jobs) {
  const job = jobs.find((item) => item.status === 'queued' || item.status === 'running');
  if (job) showBanner(`${job.stage} · ${Math.round(job.progress * 100)}%`);
  else if (jobs[0]?.status === 'failed') showBanner(jobs[0].error || 'Processing failed.', true);
  else if (jobs[0]?.status === 'completed' && ['extract', 'analyze', 'audio'].includes(jobs[0].kind)) {
    showBanner(jobs[0].stage); setTimeout(() => { if ($('#job-banner').textContent === jobs[0].stage) $('#job-banner').hidden = true; }, 4500);
  } else $('#job-banner').hidden = true;
}

async function monitorJob(jobId) {
  clearInterval(state.pollTimer);
  state.monitoredJob = jobId;
  state.pollTimer = setInterval(async () => {
    try {
      const job = await api(`/api/jobs/${jobId}`);
      showBanner(`${job.stage} · ${Math.round(job.progress * 100)}%`, job.status === 'failed');
      if (['completed', 'failed'].includes(job.status)) {
        clearInterval(state.pollTimer); state.monitoredJob = null; await reloadProject();
      }
    } catch { clearInterval(state.pollTimer); state.monitoredJob = null; }
  }, 1200);
}

$('#analyze-button').addEventListener('click', async () => {
  const button = $('#analyze-button'); button.disabled = true;
  try { await flushPassageSaves(); const result = await api(`/api/projects/${state.projectId}/analysis`, { method: 'POST' }); monitorJob(result.job_id); }
  catch (error) { showBanner(error.message, true); button.disabled = false; }
});

$('#generate-button').addEventListener('click', async () => {
  if (!confirm('Generate the audiobook now? All passages need an assigned speaker with a created voice.')) return;
  const button = $('#generate-button'); button.disabled = true;
  try { await flushPassageSaves(); const result = await api(`/api/projects/${state.projectId}/audio`, { method: 'POST' }); monitorJob(result.job_id); }
  catch (error) { showBanner(error.message, true); button.disabled = false; }
});

$('#back-button').addEventListener('click', async () => {
  clearInterval(state.pollTimer); state.projectId = null;
  $('#project-view').hidden = true; $('#home-view').hidden = false;
  await loadProjects(); window.scrollTo({ top: 0, behavior: 'smooth' });
});

$('#delete-project').addEventListener('click', async () => {
  if (!confirm('Delete this project, its PDF, and generated audio?')) return;
  try { await api(`/api/projects/${state.projectId}`, { method: 'DELETE' }); $('#back-button').click(); }
  catch (error) { showBanner(error.message, true); }
});

refreshHealth(); loadProjects().catch((error) => showBanner(error.message, true));
