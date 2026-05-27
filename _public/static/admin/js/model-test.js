let apiKey = '';
let modelList = [];
let testResults = [];
let running = false;

const byId = (id) => document.getElementById(id);
const DEFAULT_TEST_PROMPT = '你是谁？';

async function init() {
  apiKey = await ensureAdminKey();
  if (apiKey === null) return;
  setupModalOverlayClose();
  await loadModels();
  initResults();
}

async function loadModels() {
  const loading = byId('model-test-loading');
  if (loading) loading.classList.remove('hidden');
  try {
    const res = await fetch('/v1/admin/tokens/test/models', {
      cache: 'no-store',
      headers: buildAuthHeaders(apiKey)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const items = Array.isArray(data && data.data) ? data.data : [];
    modelList = items
      .map(item => item && item.id)
      .filter(Boolean);
  } catch (e) {
    showToast(t('common.loadError', { msg: e.message }), 'error');
    modelList = [];
  } finally {
    initResults();
    if (loading) loading.classList.add('hidden');
  }
}

function initResults() {
  testResults = modelList.map((modelId, index) => ({
    index: index + 1,
    model: modelId,
    status: 'idle',
    httpStatus: '',
    message: '',
    detail: null,
  }));
  renderResults();
  updateSummary();
  setStatusText(t('modelTest.ready'));
}

function setStatusText(text) {
  const status = byId('model-test-status');
  if (status) status.textContent = text;
}

function updateSummary() {
  const total = testResults.length;
  const success = testResults.filter(item => item.status === 'success').length;
  const failed = testResults.filter(item => item.status === 'failed').length;
  const finished = success + failed;
  byId('summary-total').textContent = String(total);
  byId('summary-success').textContent = String(success);
  byId('summary-failed').textContent = String(failed);
  byId('summary-progress').textContent = `${finished} / ${total}`;
}

function getStatusBadge(status) {
  if (status === 'success') {
    return `<span class="badge badge-green">${escapeHtml(t('modelTest.statusSuccess'))}</span>`;
  }
  if (status === 'failed') {
    return `<span class="badge badge-red">${escapeHtml(t('modelTest.statusFailed'))}</span>`;
  }
  if (status === 'running') {
    return `<span class="badge badge-blue">${escapeHtml(t('modelTest.statusRunning'))}</span>`;
  }
  return `<span class="badge badge-gray">${escapeHtml(t('modelTest.statusIdle'))}</span>`;
}

function renderResults() {
  const tbody = byId('model-test-table-body');
  if (!tbody) return;

  const fragment = document.createDocumentFragment();
  testResults.forEach((item, idx) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${item.index}</td>
      <td class="text-left"><span class="model-id">${escapeHtml(item.model)}</span></td>
      <td>${getStatusBadge(item.status)}</td>
      <td>${escapeHtml(item.httpStatus || '-')}</td>
      <td class="text-left"><span class="result-message">${escapeHtml(item.message || '-')}</span></td>
      <td>
        <button type="button" class="detail-btn" onclick="openDetailModal(${idx})" ${item.detail ? '' : 'disabled'}>
          ${escapeHtml(t('common.view'))}
        </button>
      </td>
    `;
    fragment.appendChild(tr);
  });

  tbody.replaceChildren(fragment);
  updateSummary();
}

async function runModelTests() {
  if (running) {
    showToast(t('common.taskInProgress'), 'info');
    return;
  }

  const tokenInput = byId('test-token-input');
  const promptInput = byId('test-prompt-input');
  const token = tokenInput ? String(tokenInput.value || '').trim() : '';
  const prompt = (promptInput ? String(promptInput.value || '').trim() : '') || DEFAULT_TEST_PROMPT;

  if (!token) {
    showToast(t('modelTest.tokenRequired'), 'error');
    return;
  }

  if (modelList.length === 0) {
    showToast(t('modelTest.noModels'), 'error');
    return;
  }

  running = true;
  const runBtn = byId('model-test-run');
  const originalText = runBtn ? runBtn.textContent : '';
  if (runBtn) {
    runBtn.disabled = true;
    runBtn.textContent = t('modelTest.testingAll');
  }

  testResults = modelList.map((modelId, index) => ({
    index: index + 1,
    model: modelId,
    status: 'idle',
    httpStatus: '',
    message: '',
    detail: null,
  }));
  renderResults();

  try {
    for (let i = 0; i < testResults.length; i++) {
      const item = testResults[i];
      item.status = 'running';
      item.message = t('modelTest.runningCurrent');
      renderResults();
      setStatusText(t('modelTest.runningStatus', { current: i + 1, total: testResults.length, model: item.model }));

      try {
        const res = await fetch('/v1/admin/tokens/test', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...buildAuthHeaders(apiKey)
          },
          body: JSON.stringify({
            token,
            model: item.model,
            message: prompt
          })
        });
        const data = await res.json();
        item.detail = data;
        item.httpStatus = data && data.response && data.response.status != null
          ? `${data.response.status} ${data.response.status_text || ''}`.trim()
          : `${res.status}`;
        item.status = res.ok && data && data.status === 'success' ? 'success' : 'failed';
        item.message = resolveResultMessage(data, res.status);
      } catch (e) {
        item.status = 'failed';
        item.httpStatus = '0';
        item.message = e.message || t('common.requestFailed');
        item.detail = {
          request: null,
          response: {
            status: 0,
            status_text: 'Request Failed',
            headers: {},
            body: item.message
          }
        };
      }

      renderResults();
    }

    const failed = testResults.filter(item => item.status === 'failed').length;
    setStatusText(
      failed > 0
        ? t('modelTest.finishedWithFailures', { failed, total: testResults.length })
        : t('modelTest.finishedAll', { total: testResults.length })
    );
    showToast(
      failed > 0
        ? t('modelTest.finishedToastWarning', { failed, total: testResults.length })
        : t('modelTest.finishedToastSuccess', { total: testResults.length }),
      failed > 0 ? 'warning' : 'success'
    );
  } finally {
    running = false;
    if (runBtn) {
      runBtn.disabled = false;
      runBtn.textContent = originalText || t('modelTest.startTest');
    }
  }
}

function resolveResultMessage(data, httpStatus) {
  if (!data) return `HTTP ${httpStatus}`;
  if (data.status === 'success') {
    return t('modelTest.resultSuccess');
  }
  if (data.detail) return String(data.detail);
  if (data.error) return String(data.error);
  if (data.response && data.response.body) {
    return summarizeText(data.response.body);
  }
  return `HTTP ${httpStatus}`;
}

function summarizeText(value) {
  const text = typeof value === 'string' ? value : formatJson(value);
  if (!text) return '-';
  const normalized = text.replace(/\s+/g, ' ').trim();
  return normalized.length > 120 ? normalized.slice(0, 120) + '...' : normalized;
}

function openDetailModal(index) {
  const item = testResults[index];
  if (!item || !item.detail) return;

  byId('model-test-detail-title').textContent = t('modelTest.detailTitle', { model: item.model });
  byId('detail-request-url').textContent = item.detail.request && item.detail.request.url ? item.detail.request.url : '-';
  byId('detail-request-headers').textContent = formatJson(item.detail.request && item.detail.request.headers);
  byId('detail-request-body').textContent = formatJson(item.detail.request && item.detail.request.body);

  const response = item.detail.response || {};
  const statusEl = byId('detail-response-status');
  const status = response.status != null ? `${response.status} ${response.status_text || ''}`.trim() : '-';
  statusEl.textContent = status;
  statusEl.className = response.status >= 200 && response.status < 300 ? 'text-green-600 ml-2' : 'text-red-600 ml-2';
  byId('detail-response-headers').textContent = formatJson(response.headers);
  byId('detail-response-body').textContent = formatJson(response.body);

  openModal('model-test-detail-modal');
}

function openModal(id) {
  const modal = byId(id);
  if (!modal) return;
  modal.classList.remove('hidden');
  requestAnimationFrame(() => {
    modal.classList.add('is-open');
  });
}

function closeModal(id) {
  const modal = byId(id);
  if (!modal) return;
  modal.classList.remove('is-open');
  setTimeout(() => {
    modal.classList.add('hidden');
  }, 200);
}

function closeDetailModal() {
  closeModal('model-test-detail-modal');
}

function setupModalOverlayClose() {
  const modal = byId('model-test-detail-modal');
  if (!modal) return;
  modal.addEventListener('click', (event) => {
    if (event.target === modal) {
      closeDetailModal();
    }
  });
}

function formatJson(obj) {
  if (!obj) return '-';
  try {
    if (typeof obj === 'string') {
      try {
        const parsed = JSON.parse(obj);
        return JSON.stringify(parsed, null, 2);
      } catch {
        return obj;
      }
    }
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

function escapeHtml(text) {
  if (text == null) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

window.onload = init;
