// Global API helper for backend communication
// Keeps headers and endpoints consistent; Pico.css unaffected


(function initAPI(global) {
  // Default production base URL (HTTPS for Chrome Web Store readiness)
  let API_BASE_URL = 'https://cv.kroete.io';
  const LLM_PROVIDER = 'openai';
  const LLM_MODEL = 'gpt-4o'; // Recommended default
  let OPENAI_KEY = '';

  async function loadConfig() {
    const local = await new Promise((resolve) => {
      chrome.storage.local.get(['openaiKey', 'apiBaseUrl'], resolve);
    });
    API_BASE_URL = local?.apiBaseUrl || API_BASE_URL;
    OPENAI_KEY = local?.openaiKey || '';
    return { provider: LLM_PROVIDER, model: LLM_MODEL, baseUrl: API_BASE_URL };
  }

  function ensureKey() {
    const key = OPENAI_KEY || '';
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
    headers.set('X-LLM-Model', LLM_MODEL);
    if (OPENAI_KEY) headers.set('X-OpenAI-Key', OPENAI_KEY);
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

  async function analyzeCV(file, DEBUG = false, jobContext = null) {
    ensureKey();
    const formData = new FormData();
    if (file) {
      if (DEBUG) console.log('Uploading CV file:', file.name);
      formData.append('file', file, file.name);
    } else {
      throw new Error('No file provided');
    }

    const headers = { 'Accept': 'application/json' };
    // Add job context for more targeted CV analysis
    if (jobContext && typeof jobContext === 'string' && jobContext.trim()) {
      headers['X-Job-Context'] = jobContext.trim().substring(0, 10000); // Limit context size
    }

    const response = await apiFetch(`/analyze-cv`, {
      method: 'POST',
      headers,
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

  // Removed server-side CV listing/deletion to avoid retention

  global.API = { loadConfig, analyzeJobDescription, analyzeCV, getMatchingScore, getBaseUrl: () => API_BASE_URL };
})(window);
