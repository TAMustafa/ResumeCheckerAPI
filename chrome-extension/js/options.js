document.addEventListener('DOMContentLoaded', async () => {
  // Elements (OpenAI-only)
  const apiKeyEl = document.getElementById('apiKey');
  const saveBtn = document.getElementById('saveBtn');
  const testBtn = document.getElementById('testBtn');
  const removeBtn = document.getElementById('removeBtn');
  const statusEl = document.getElementById('status');
  const privacyLink = document.getElementById('privacyLink');
  const termsLink = document.getElementById('termsLink');

  // Backend URL: prefer stored override, else default to current IP
  const localCfg = await new Promise((resolve) => chrome.storage.local.get(['apiBaseUrl'], resolve));
  const API_BASE_URL = localCfg?.apiBaseUrl || 'https://cv.kroete.io';

  function setStatus(msg, ok = true) {
    statusEl.textContent = msg;
    statusEl.style.color = ok ? '#065f46' : '#991b1b';
    if (ok) setTimeout(() => (statusEl.textContent = ''), 2500);
  }

  const local = await new Promise((resolve) => chrome.storage.local.get(['openaiKey'], resolve));
  apiKeyEl.value = local?.openaiKey || '';

  // Set placeholder links (replace when you have live URLs)
  if (privacyLink) privacyLink.href = 'https://cv.kroete.io/privacy';
  if (termsLink) termsLink.href = 'https://cv.kroete.io/terms';

  // Harden: explicitly open external links in a new tab even if stale HTML had '#'
  if (privacyLink) {
    privacyLink.addEventListener('click', (e) => {
      try {
        e.preventDefault();
        window.open('https://cv.kroete.io/privacy', '_blank');
      } catch (_) { /* no-op */ }
    });
  }
  if (termsLink) {
    termsLink.addEventListener('click', (e) => {
      try {
        e.preventDefault();
        window.open('https://cv.kroete.io/terms', '_blank');
      } catch (_) { /* no-op */ }
    });
  }

  // No provider or model options; OpenAI gpt-4o is assumed.

  saveBtn.addEventListener('click', async () => {
    const key = apiKeyEl.value.trim();
    await new Promise((resolve) => chrome.storage.local.set({ openaiKey: key }, resolve));
    setStatus('Saved.');
  });

  removeBtn.addEventListener('click', async () => {
    await new Promise((resolve) => chrome.storage.local.set({ openaiKey: '' }, resolve));
    apiKeyEl.value = '';
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

  // No purge functionality (no server-side retention)
});
