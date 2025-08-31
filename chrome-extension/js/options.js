document.addEventListener('DOMContentLoaded', () => {
  const providerEl = document.getElementById('provider');
  const apiKeyEl = document.getElementById('apiKey');
  const modelEl = document.getElementById('model');
  const saveBtn = document.getElementById('saveBtn');
  const testBtn = document.getElementById('testBtn');
  const removeBtn = document.getElementById('removeBtn');
  const statusEl = document.getElementById('status');

  // Default backend URL is fixed; users shouldn't change it
  const API_BASE_URL = 'http://91.98.122.7';

  function setStatus(msg, ok = true) {
    statusEl.textContent = msg;
    statusEl.style.color = ok ? '#065f46' : '#991b1b';
    if (ok) setTimeout(() => (statusEl.textContent = ''), 2500);
  }

  chrome.storage.sync.get(['llmProvider', 'llmKeys', 'llmModels'], (items) => {
    const provider = 'openai';
    const keys = items?.llmKeys || {};
    const models = items?.llmModels || {};
    providerEl.value = 'openai';
    apiKeyEl.value = keys[provider] || '';
    // default model for OpenAI if empty
    const defaults = { openai: 'gpt-4o' };
    modelEl.value = models[provider] || defaults[provider] || '';
  });

  providerEl.addEventListener('change', () => {
    // Load the key for the selected provider
    const provider = providerEl.value;
    chrome.storage.sync.get(['llmKeys', 'llmModels'], (items) => {
      const keys = items?.llmKeys || {};
      const models = items?.llmModels || {};
      apiKeyEl.value = keys[provider] || '';
      const defaults = { openai: 'gpt-4o' };
      modelEl.value = models[provider] || defaults[provider] || '';
    });
  });

  saveBtn.addEventListener('click', () => {
    const provider = providerEl.value;
    const key = apiKeyEl.value.trim();
    const model = modelEl.value.trim();
    chrome.storage.sync.get(['llmKeys', 'llmModels'], (items) => {
      const keys = { ...(items?.llmKeys || {}) };
      if (key) keys[provider] = key; else delete keys[provider];
      const models = { ...(items?.llmModels || {}) };
      if (model) models[provider] = model; else delete models[provider];
      // For backward compatibility, keep 'openaiKey' updated when provider is openai
      const extra = provider === 'openai' ? { openaiKey: key } : {};
      chrome.storage.sync.set({ llmProvider: provider, llmKeys: keys, llmModels: models, ...extra }, () => {
        setStatus('Saved.');
      });
    });
  });

  removeBtn.addEventListener('click', () => {
    const provider = providerEl.value;
    chrome.storage.sync.get(['llmKeys', 'llmModels'], (items) => {
      const keys = { ...(items?.llmKeys || {}) };
      delete keys[provider];
      const models = { ...(items?.llmModels || {}) };
      delete models[provider];
      // If removing openai, also clear legacy key
      const extra = provider === 'openai' ? { openaiKey: '' } : {};
      chrome.storage.sync.set({ llmKeys: keys, llmModels: models, ...extra }, () => {
        apiKeyEl.value = '';
        modelEl.value = '';
        setStatus('Key removed.');
      });
    });
  });

  testBtn.addEventListener('click', async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/healthz`);
      setStatus(resp.ok ? 'Connection OK.' : `Failed: ${resp.status}`, resp.ok);
    } catch (e) {
      setStatus(`Failed: ${e.message}`, false);
    }
  });
});
