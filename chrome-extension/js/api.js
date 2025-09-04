// Global API helper for backend communication
// Keeps headers and endpoints consistent; Pico.css unaffected

(function initAPI(global) {
  // Default base URL (IP for now). Will switch to HTTPS domain later.
  let API_BASE_URL = 'http://91.98.122.7';
  let LLM_PROVIDER = 'openai';
  let LLM_KEYS = {}; // { openai, deepseek, anthropic }
  let LLM_MODELS = {}; // per-provider model mapping
  let LLM_MODEL = 'gpt-4o';

  async function loadConfig() {
    // Prefer local storage for sensitive keys; optionally merge from sync if user opted in
    const local = await new Promise((resolve) => {
      chrome.storage.local.get(['llmProvider', 'llmKeys', 'llmModels', 'openaiKey', 'apiBaseUrl', 'syncKeysOptIn'], resolve);
    });
    const syncOptIn = !!local?.syncKeysOptIn;
    let sync = {};
    if (syncOptIn) {
      sync = await new Promise((resolve) => {
        chrome.storage.sync.get(['llmProvider', 'llmKeys', 'llmModels', 'openaiKey'], resolve);
      });
    }

    // Base URL: allow override via storage, else default to IP
    API_BASE_URL = local?.apiBaseUrl || API_BASE_URL;

    // Force OpenAI as provider for now
    LLM_PROVIDER = 'openai';
    // Merge precedence: local first, then sync fallback
    LLM_KEYS = (local?.llmKeys) || (sync?.llmKeys) || {};
    if (!LLM_KEYS.openai && (local?.openaiKey || sync?.openaiKey)) {
      LLM_KEYS.openai = local?.openaiKey || sync?.openaiKey || '';
    }
    LLM_MODELS = (local?.llmModels) || (sync?.llmModels) || {};
    LLM_MODEL = LLM_MODELS[LLM_PROVIDER] || 'gpt-4o';

    return { provider: LLM_PROVIDER, model: LLM_MODEL, baseUrl: API_BASE_URL };
  }

  function ensureKey() {
    const key = (LLM_KEYS && LLM_KEYS[LLM_PROVIDER]) || '';
    if (!key || key.trim().length === 0) {
      alert('Please set your LLM API key in the extension Options first.');
      if (chrome.runtime.openOptionsPage) chrome.runtime.openOptionsPage();
      throw new Error('Missing LLM API key');
    }
  }

  async function apiFetch(path, options = {}) {
    const url = path.startsWith('http') ? path : `${API_BASE_URL}${path}`;
    const headers = new Headers(options.headers || {});
    headers.set('X-LLM-Provider', LLM_PROVIDER);
    if (LLM_MODEL) headers.set('X-LLM-Model', LLM_MODEL);
    const keyForProvider = (LLM_KEYS && LLM_KEYS[LLM_PROVIDER]) || '';
    if (keyForProvider) headers.set('X-OpenAI-Key', keyForProvider);
    return fetch(url, { ...options, headers });
  }

  async function analyzeJobDescription(description, DEBUG = false) {
    ensureKey();
    if (DEBUG) console.log('Sending job description to analyze:', description);
    const response = await apiFetch(`/analyze-job-vacancy`, {
      method: 'POST',
      headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ vacancy_text: description })
    });
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Server responded with:', errorText);
      throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }
    return await response.json();
  }

  async function analyzeCV(file, DEBUG = false) {
    ensureKey();
    const formData = new FormData();
    if (file && file.isFromDropdown) {
      if (DEBUG) console.log('Analyzing CV from dropdown:', file.name);
      const encodedFilename = encodeURIComponent(file.name);
      const response = await apiFetch(`/uploaded_cvs/${encodedFilename}`);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to fetch CV: ${response.status} - ${errorText}`);
      }
      const blob = await response.blob();
      if (blob.size === 0) throw new Error('Received empty file from server');
      const fetchedFile = new File([blob], file.name, { type: 'application/pdf' });
      formData.append('file', fetchedFile, file.name);
    } else if (file) {
      if (DEBUG) console.log('Uploading CV file:', file.name);
      formData.append('file', file, file.name);
    } else {
      throw new Error('No file provided');
    }

    const response = await apiFetch(`/analyze-cv`, {
      method: 'POST',
      headers: { 'Accept': 'application/json' },
      body: formData
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`CV analysis failed: ${response.status} - ${errorText}`);
    }
    return await response.json();
  }

  async function getMatchingScore(cvAnalysis, jobRequirements) {
    ensureKey();
    const response = await apiFetch(`/score-cv-match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cv_analysis: cvAnalysis, job_requirements: jobRequirements })
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  }

  async function fetchUploadedCVs() {
    const response = await apiFetch(`/api/uploaded-cvs`);
    if (!response.ok) throw new Error('Failed to fetch CVs');
    return await response.json();
  }

  async function deleteUploadedCv(filename) {
    const resp = await apiFetch(`/api/uploaded-cvs/${encodeURIComponent(filename)}`, { method: 'DELETE' });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`Failed to delete: ${resp.status} ${text}`);
    }
  }

  global.API = {
    loadConfig,
    analyzeJobDescription,
    analyzeCV,
    getMatchingScore,
    fetchUploadedCVs,
    deleteUploadedCv,
    getBaseUrl: () => API_BASE_URL,
  };
})(window);
