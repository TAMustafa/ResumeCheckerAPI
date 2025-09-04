document.addEventListener('DOMContentLoaded', async () => {
  const providerEl = document.getElementById('provider');
  const apiKeyEl = document.getElementById('apiKey');
  const modelEl = document.getElementById('model');
  const saveBtn = document.getElementById('saveBtn');
  const testBtn = document.getElementById('testBtn');
  const removeBtn = document.getElementById('removeBtn');
  const purgeBtn = document.getElementById('purgeBtn');
  const statusEl = document.getElementById('status');
  const syncOptInEl = document.getElementById('syncOptIn');
  const privacyLink = document.getElementById('privacyLink');
  const termsLink = document.getElementById('termsLink');

  // Backend URL: prefer stored override, else default to current IP
  const localCfg = await new Promise((resolve) => chrome.storage.local.get(['apiBaseUrl', 'syncKeysOptIn'], resolve));
  const API_BASE_URL = localCfg?.apiBaseUrl || 'http://91.98.122.7';

  function setStatus(msg, ok = true) {
    statusEl.textContent = msg;
    statusEl.style.color = ok ? '#065f46' : '#991b1b';
    if (ok) setTimeout(() => (statusEl.textContent = ''), 2500);
  }

  // Load settings from local first; if syncOptIn is true, merge sync as fallback
  const syncOptIn = !!localCfg?.syncKeysOptIn;
  const local = await new Promise((resolve) => chrome.storage.local.get(['llmProvider', 'llmKeys', 'llmModels', 'openaiKey', 'syncKeysOptIn'], resolve));
  let sync = {};
  if (syncOptIn) {
    sync = await new Promise((resolve) => chrome.storage.sync.get(['llmProvider', 'llmKeys', 'llmModels', 'openaiKey'], resolve));
  }

  const provider = 'openai';
  const keys = local?.llmKeys || sync?.llmKeys || {};
  const models = local?.llmModels || sync?.llmModels || {};
  providerEl.value = provider;
  apiKeyEl.value = keys[provider] || local?.openaiKey || sync?.openaiKey || '';
  const defaults = { openai: 'gpt-4o' };
  modelEl.value = models[provider] || defaults[provider] || '';
  if (syncOptInEl) syncOptInEl.checked = !!local?.syncKeysOptIn;

  // Set placeholder links (replace when you have live URLs)
  if (privacyLink) privacyLink.href = '#';
  if (termsLink) termsLink.href = '#';

  providerEl.addEventListener('change', async () => {
    // Load the key for the selected provider from local (then sync fallback if opted-in)
    const provider = providerEl.value;
    const local = await new Promise((resolve) => chrome.storage.local.get(['llmKeys', 'llmModels', 'openaiKey', 'syncKeysOptIn'], resolve));
    const syncOptIn = !!local?.syncKeysOptIn;
    let sync = {};
    if (syncOptIn) sync = await new Promise((resolve) => chrome.storage.sync.get(['llmKeys', 'llmModels', 'openaiKey'], resolve));
    const keys = local?.llmKeys || sync?.llmKeys || {};
    const models = local?.llmModels || sync?.llmModels || {};
    apiKeyEl.value = keys[provider] || local?.openaiKey || sync?.openaiKey || '';
    const defaults = { openai: 'gpt-4o' };
    modelEl.value = models[provider] || defaults[provider] || '';
  });

  saveBtn.addEventListener('click', async () => {
    const provider = providerEl.value;
    const key = apiKeyEl.value.trim();
    const model = modelEl.value.trim();
    const syncOptIn = !!(syncOptInEl && syncOptInEl.checked);

    // Save to local by default
    const existingLocal = await new Promise((resolve) => chrome.storage.local.get(['llmKeys', 'llmModels'], resolve));
    const keys = { ...(existingLocal?.llmKeys || {}) };
    if (key) keys[provider] = key; else delete keys[provider];
    const models = { ...(existingLocal?.llmModels || {}) };
    if (model) models[provider] = model; else delete models[provider];
    const extra = provider === 'openai' ? { openaiKey: key } : {};
    await new Promise((resolve) => chrome.storage.local.set({ llmProvider: provider, llmKeys: keys, llmModels: models, syncKeysOptIn: syncOptIn, ...extra }, resolve));

    // Optionally mirror to sync if opted-in
    if (syncOptIn) {
      const syncPayload = { llmProvider: provider, llmKeys: keys, llmModels: models, ...extra };
      await new Promise((resolve) => chrome.storage.sync.set(syncPayload, resolve));
    }
    setStatus('Saved.');
  });

  removeBtn.addEventListener('click', async () => {
    const provider = providerEl.value;
    const local = await new Promise((resolve) => chrome.storage.local.get(['llmKeys', 'llmModels', 'syncKeysOptIn'], resolve));
    const keys = { ...(local?.llmKeys || {}) };
    delete keys[provider];
    const models = { ...(local?.llmModels || {}) };
    delete models[provider];
    const extra = provider === 'openai' ? { openaiKey: '' } : {};
    await new Promise((resolve) => chrome.storage.local.set({ llmKeys: keys, llmModels: models, ...extra }, resolve));
    if (local?.syncKeysOptIn) {
      await new Promise((resolve) => chrome.storage.sync.set({ llmKeys: keys, llmModels: models, ...extra }, resolve));
    }
    apiKeyEl.value = '';
    modelEl.value = '';
    setStatus('Key removed.');
  });

  testBtn.addEventListener('click', async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/healthz`);
      setStatus(resp.ok ? 'Connection OK.' : `Failed: ${resp.status}`, resp.ok);
    } catch (e) {
      setStatus(`Failed: ${e.message}`, false);
    }
  });

  if (purgeBtn) {
    purgeBtn.addEventListener('click', async () => {
      const ok = confirm('This will permanently delete any stored CV files on the server. Continue?');
      if (!ok) return;
      try {
        const resp = await fetch(`${API_BASE_URL}/api/purge`, { method: 'POST' });
        if (!resp.ok) {
          const text = await resp.text();
          setStatus(`Purge failed: ${resp.status} ${text}`, false);
          return;
        }
        const data = await resp.json();
        const deleted = typeof data?.deleted_files === 'number' ? data.deleted_files : 0;
        setStatus(`Purged. Deleted files: ${deleted}.`);
      } catch (e) {
        setStatus(`Purge failed: ${e.message}`, false);
      }
    });
  }
});
