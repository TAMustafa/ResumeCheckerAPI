// Networking is handled in js/api.js via the global API namespace.

// Tab logic
const tabJobBtn = document.getElementById('tab-job');
const tabCvBtn = document.getElementById('tab-cv');
const tabResultBtn = document.getElementById('tab-result');
const tabBtns = [tabJobBtn, tabCvBtn, tabResultBtn];
const tabSections = [
  document.getElementById('section-job'),
  document.getElementById('section-cv'),
  document.getElementById('section-result')
];

function switchToTab(idx) {
  tabBtns.forEach((b, i) => {
    b.classList.toggle('active', i === idx);
    b.setAttribute('aria-selected', i === idx ? 'true' : 'false');
    tabSections[i].classList.toggle('active', i === idx);
  });
}

tabJobBtn.addEventListener('click', () => switchToTab(0));
tabCvBtn.addEventListener('click', () => switchToTab(1));
tabResultBtn.addEventListener('click', async () => {
  if (tabResultBtn.disabled || isAnalyzing) return;
  await analyzeDocuments();
});

// DOM Elements (update selectors for new structure)
const cvUpload = document.getElementById('cv-upload');
const uploadBtn = document.getElementById('upload-btn');
const fileName = document.getElementById('file-name');
const jobDescription = document.getElementById('job-description');
const resultsSection = document.getElementById('results');
const matchScore = document.getElementById('match-score');
const overallExplanation = document.getElementById('overall-explanation');

// Results lists (chips for Matches & Misses removed)
const strengthsList = document.getElementById('strengths-list');
const gapsList = document.getElementById('gaps-list');
// removed: matched/missing chip containers
const suggestionsList = document.getElementById('suggestions-list');
// Per-category explanations
const techExplanation = document.getElementById('tech-explanation');
const softExplanation = document.getElementById('soft-explanation');
const expExplanation = document.getElementById('exp-explanation');
const qualExplanation = document.getElementById('qual-explanation');
const respExplanation = document.getElementById('resp-explanation');

// New DOM elements for individual analysis
const analyzeJobBtn = document.getElementById('analyze-job-btn');
const jobAnalysisSummary = document.getElementById('job-analysis-summary');
const cvAnalysisSummary = document.getElementById('cv-analysis-summary');

let isAnalyzing = false;
const DEBUG = false; // local debug flag
async function loadConfig() { return API.loadConfig(); }

// Progress elements
const techSkillsProgress = document.getElementById('tech-skills-progress');
const experienceProgress = document.getElementById('experience-progress');
const techSkillsText = document.getElementById('tech-skills-text');
const softSkillsProgress = document.getElementById('soft-skills-progress');
const softSkillsText = document.getElementById('soft-skills-text');
const experienceText = document.getElementById('experience-text');
const responsibilitiesProgress = document.getElementById('responsibilities-progress');
const responsibilitiesText = document.getElementById('responsibilities-text');

// State
let cvFile = null;
let jobRequirements = null;
let cvAnalysis = null;

// Store last cvAnalysis for strengths/gaps fallback
let lastCvAnalysis = null;

// Session cache configuration (20 MB cap)
const MAX_CV_SIZE_BYTES = 20 * 1024 * 1024;

// Event Listeners
uploadBtn.addEventListener('click', () => cvUpload.click());
cvUpload.addEventListener('change', handleFileUpload);
jobDescription.addEventListener('input', validateForm);
// When job text changes, invalidate previous job analysis
jobDescription.addEventListener('input', () => { jobRequirements = null; });

// Analyze Job Description (individual)
analyzeJobBtn.addEventListener('click', async () => {
  const desc = jobDescription.value.trim();
  jobAnalysisSummary.innerHTML = '';
  
  // Input validation
  if (!desc) {
    jobAnalysisSummary.innerHTML = '<p class="error">Please enter a job description.</p>';
    return;
  }
  
  if (desc.length < 50) {
    jobAnalysisSummary.innerHTML = '<p class="error">Job description seems too short. Please provide more details.</p>';
    return;
  }
  
  if (desc.length > 50000) {
    jobAnalysisSummary.innerHTML = '<p class="error">Job description is too long. Please keep it under 50,000 characters.</p>';
    return;
  }
  
  analyzeJobBtn.disabled = true;
  jobAnalysisSummary.innerHTML = '<p>Analyzing job description... <span class="loading-dots"></span></p>';
  
  try {
    const result = await analyzeJobDescription(desc);
    jobRequirements = result; // cache analyzed job requirements
    jobAnalysisSummary.innerHTML = renderJobAnalysisSummary(result);
    validateForm();
  } catch (e) {
    console.error('Job analysis error:', e);
    const errorMsg = e.message?.includes('too large') 
      ? 'Job description is too large. Please shorten it and try again.'
      : e.message?.includes('Failed to fetch')
      ? 'Could not connect to the analysis service. Please check your internet connection.'
      : 'Error analyzing job description. Please try again.';
    jobAnalysisSummary.innerHTML = `<p class="error">${errorMsg}</p>`;
  }
  analyzeJobBtn.disabled = false;
});

// Analyze CV now happens automatically on file selection (see handleFileUpload)

// No Clear or Analyze buttons in Result tab anymore

document.addEventListener('DOMContentLoaded', async () => {
  await loadConfig();
  resetResults();
  validateForm();
  // Removed fetching of server-stored CVs (no retention)

  // Try to restore CV from session storage for this browser session
  await restoreCvFromSession();

  // Settings button -> open options page
  const settingsBtn = document.getElementById('open-settings');
  if (settingsBtn) {
    settingsBtn.addEventListener('click', () => {
      if (chrome.runtime?.openOptionsPage) {
        chrome.runtime.openOptionsPage();
      } else {
        window.open(chrome.runtime.getURL('options.html'));
      }
    });
  }
});

// Removed server-stored CV dropdown and related handlers

// Update the file name display when a file is selected
function handleFileUpload(event) {
  const file = event.target.files[0];
  
  // No dropdown to reset (no server retention)
  
  if (file && file.type === 'application/pdf') {
    cvFile = file;
    // Invalidate previous CV analysis when a new file is chosen
    lastCvAnalysis = null;
    // Truncate long file names
    const maxLength = 30;
    const displayName = file.name.length > maxLength 
      ? file.name.substring(0, maxLength - 3) + '...' 
      : file.name;
    fileName.textContent = displayName;
    fileName.title = file.name; // Show full name on hover
    // Auto-trigger CV analysis
    autoAnalyzeCv();
    // Save to session storage (best-effort)
    saveCvToSession(file).catch(() => {/* ignore session save errors */});
  } else {
    cvFile = null;
    fileName.textContent = 'No file chosen';
    lastCvAnalysis = null;
  }
  validateForm();
  resetResults();
}

async function autoAnalyzeCv() {
  if (!cvFile) return;
  cvAnalysisSummary.innerHTML = '';
  cvAnalysisSummary.innerHTML = '<p>Analyzing CV... <span class="loading-dots"></span></p>';
  try {
    // Pass job description as context for more targeted CV analysis
    const jobContext = jobDescription.value.trim() || null;
    const result = await analyzeCV(cvFile, DEBUG, jobContext);
    lastCvAnalysis = result;
    cvAnalysisSummary.innerHTML = renderCvAnalysisSummary(result);
    validateForm();
  } catch (e) {
    console.error('CV analysis error:', e);
    const errorMsg = e.message?.includes('Failed to fetch')
      ? 'Could not connect to the analysis service. Please check your internet connection.'
      : 'Error analyzing CV. Please try again.';
    cvAnalysisSummary.innerHTML = `<p class="error">${errorMsg}</p>`;
  }
}

// Persist the uploaded CV for this browser session only
async function saveCvToSession(file) {
  try {
    if (!file) return;
    if (typeof chrome === 'undefined' || !chrome.storage?.session) return; // not available (e.g., tests)
    if (file.size > MAX_CV_SIZE_BYTES) {
      console.warn('CV is too large for session cache, skipping save');
      return;
    }
    const buffer = await file.arrayBuffer();
    const payload = { name: file.name, type: file.type, size: file.size, buffer };
    await new Promise((resolve) => chrome.storage.session.set({ cvSession: payload }, resolve));
  } catch (err) {
    console.warn('Failed to save CV to session storage:', err);
  }
}

// Restore CV from session cache if present
async function restoreCvFromSession() {
  try {
    if (typeof chrome === 'undefined' || !chrome.storage?.session) return false;
    const data = await new Promise((resolve) => chrome.storage.session.get(['cvSession'], resolve));
    const entry = data?.cvSession;
    if (!entry || !entry.buffer || !entry.name || !entry.type) return false;

    // Reconstruct a File from the stored ArrayBuffer
    const blob = new Blob([entry.buffer], { type: entry.type });
    const restored = new File([blob], entry.name, { type: entry.type });
    cvFile = restored;
    lastCvAnalysis = null; // ensure fresh analysis

    const maxLength = 30;
    const displayName = restored.name.length > maxLength
      ? restored.name.substring(0, maxLength - 3) + '...'
      : restored.name;
    fileName.textContent = displayName;
    fileName.title = restored.name;

    // Automatically analyze the restored CV
    await autoAnalyzeCv();
    return true;
  } catch (err) {
    console.warn('Failed to restore CV from session storage:', err);
    return false;
  }
}

// Enable/disable analyze button based on form validity
function validateForm() {
  // Enable Result tab ONLY when both analyses are already completed
  const ready = !!(jobRequirements && lastCvAnalysis);
  tabResultBtn.disabled = !ready;
}

// Reset results when user changes input
cvUpload.addEventListener('change', resetResults);
jobDescription.addEventListener('input', resetResults);

function resetResults() {
  resultsSection.classList.add('hidden');
  matchScore.textContent = '0%';
  document.querySelector('.score-circle').style.setProperty('--progress', '0%');
  overallExplanation.textContent = '';
  
  // Reset progress bars
  [techSkillsProgress, softSkillsProgress, experienceProgress, responsibilitiesProgress].forEach(p => p && (p.value = 0));
  
  techSkillsText.textContent = '0%';
  if (softSkillsText) softSkillsText.textContent = '0%';
  experienceText.textContent = '0%';
  // no qualifications text anymore
  if (responsibilitiesText) responsibilitiesText.textContent = '0%';
  
  // Clear previous lists/chips
  if (strengthsList) strengthsList.innerHTML = '';
  if (gapsList) gapsList.innerHTML = '';
  if (suggestionsList) suggestionsList.innerHTML = '';
  if (techExplanation) techExplanation.textContent = '';
  if (softExplanation) softExplanation.textContent = '';
  if (expExplanation) expExplanation.textContent = '';
  // no qualifications explanation anymore
  if (respExplanation) respExplanation.textContent = '';

  // Hide optional sections/titles initially
  hideElementById('strengths-gaps', true);
  hideElementById('suggestions', true);
}

// clearAll() was unused and has been removed

// Removed delete button logic (no server retention)

// Main function to handle document analysis
async function analyzeDocuments() {
  // Guard: need either text or analyzed job, and either file/selected CV or analyzed CV
  if (!(jobRequirements || jobDescription.value.trim())) return;
  if (!(cvFile || lastCvAnalysis)) return;

  try {
    setLoading(true);

    // Step 1: Analyze job description if not already done
    if (!jobRequirements) {
      jobRequirements = await analyzeJobDescription(jobDescription.value);
    }

    // Step 2: Analyze CV if not already done
    if (!lastCvAnalysis) {
      const jobContext = jobDescription.value.trim() || null;
      cvAnalysis = await analyzeCV(cvFile, DEBUG, jobContext);
      lastCvAnalysis = cvAnalysis; // Save for later use
    }

    // Step 3: Get matching score
    const score = await getMatchingScore(lastCvAnalysis, jobRequirements);

    // Step 4: Update UI with results
    updateResultsUI(score, lastCvAnalysis);

    // Show results and switch to Result tab
    resultsSection.classList.remove('hidden');
    switchToTab(2);
  } catch (error) {
    console.error('Error analyzing documents:', error);
    alert(
      error?.message?.includes('Failed to fetch')
        ? 'Could not connect to backend. Is the API running?'
        : (error?.message || 'An error occurred while analyzing the documents. Please try again.')
    );
  } finally {
    setLoading(false);
  }
}

// API: Analyze job description
async function analyzeJobDescription(description) {
  return API.analyzeJobDescription(description, DEBUG);
}

// API: Analyze CV
async function analyzeCV(file) { return API.analyzeCV(file, DEBUG); }

// API: Get matching score
async function getMatchingScore(cvAnalysis, jobRequirements) { return API.getMatchingScore(cvAnalysis, jobRequirements); }

// Update the UI with the analysis results
function updateResultsUI(score, cvAnalysis) {
  // Update overall score
  // Ensure the score is a number and not hardcoded
  let overall = typeof score.overall_match_score === 'number' ? score.overall_match_score : 0;
  matchScore.textContent = `${overall}%`;
  overallExplanation.textContent = score.overall_explanation ?? 'No explanation available.';
  // Update circular progress visualization
  const circle = document.querySelector('.score-circle');
  if (circle) circle.style.setProperty('--progress', `${overall}%`);
  
  // Update progress bars
  updateProgressBar(techSkillsProgress, score.technical_skills_score);
  updateProgressBar(softSkillsProgress, score.soft_skills_score);
  updateProgressBar(experienceProgress, score.experience_score);
  updateProgressBar(responsibilitiesProgress, score.key_responsibilities_score);
  
  // Update score texts
  techSkillsText.textContent = `${score.technical_skills_score ?? 0}%`;
  if (softSkillsText) softSkillsText.textContent = `${score.soft_skills_score ?? 0}%`;
  experienceText.textContent = `${score.experience_score ?? 0}%`;
  // no qualifications text anymore
  if (responsibilitiesText) responsibilitiesText.textContent = `${score.key_responsibilities_score ?? 0}%`;

  // No summary-div to avoid duplication; chips and lists below present details

  // Populate enhanced sections using helpers (keeps Pico.css unaffected)
  if (typeof UI !== 'undefined') {
    // Strengths & gaps (prefer backend scoring if available; fallback to CV analysis)
    const strengths = UI.safeArray(score.strengths?.length ? score.strengths : (cvAnalysis?.candidate_suitability?.strengths || []));
    const gaps = UI.safeArray(score.gaps?.length ? score.gaps : (cvAnalysis?.candidate_suitability?.gaps || []));
    if (strengthsList) UI.setList(strengthsList, strengths);
    if (gapsList) UI.setList(gapsList, gaps);

    // Hide Strengths & Gaps section if both empty
    const hasStrengthsOrGaps = (strengths && strengths.length) || (gaps && gaps.length);
    hideElementById('strengths-gaps', !hasStrengthsOrGaps);

    // Removed Matches & Misses chips rendering

    // Suggestions list: use improvement_suggestions from schema
    const uniqueSuggestions = Array.from(new Set(Array.isArray(score.improvement_suggestions) ? score.improvement_suggestions : []));
    UI.setList(suggestionsList, uniqueSuggestions);
    hideElementById('suggestions', !(uniqueSuggestions && uniqueSuggestions.length));

    // Per-category explanations if provided by backend
    // Try multiple common keys for robustness
    if (techExplanation) techExplanation.textContent = score.technical_skills_explanation || '';
    if (softExplanation) softExplanation.textContent = score.soft_skills_explanation || '';
    if (expExplanation) expExplanation.textContent = score.experience_explanation || '';
    // no qualifications explanation anymore
    if (respExplanation) respExplanation.textContent = score.key_responsibilities_explanation || '';

    // Hide empty explanation blocks and the container if all empty
    const techHas = !!(techExplanation && techExplanation.textContent.trim());
    const softHas = !!(softExplanation && softExplanation.textContent.trim());
    const expHas = !!(expExplanation && expExplanation.textContent.trim());
    const qualHas = false; // removed qualifications
    const respHas = !!(respExplanation && respExplanation.textContent.trim());

    toggleExplanationVisibility('tech-explanation', techHas);
    toggleExplanationVisibility('soft-explanation', softHas);
    toggleExplanationVisibility('exp-explanation', expHas);
    // qualifications explanation removed
    toggleExplanationVisibility('resp-explanation', respHas);

    const explanationsContainer = document.getElementById('category-explanations');
    if (explanationsContainer) explanationsContainer.style.display = (techHas || softHas || expHas || qualHas || respHas) ? '' : 'none';
  }
}

// Utility: hide an element by id when condition is true
function hideElementById(id, hide) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.display = hide ? 'none' : '';
}

// Utility: hide the parent card/row of an explanation paragraph when empty
function toggleExplanationVisibility(id, hasContent) {
  const p = document.getElementById(id);
  if (!p) return;
  const container = p.closest('div');
  if (!container) return;
  container.style.display = hasContent ? '' : 'none';
}

// Helper function to update a progress bar
function updateProgressBar(progressElement, percentage) {
  progressElement.value = percentage ?? 0;
}

// Set loading state
function setLoading(loading) {
  isAnalyzing = loading;
  // compute readiness the same way as validateForm (both analyses done)
  const ready = !!(jobRequirements && lastCvAnalysis);
  // Disable all tabs during analysis, and keep Result disabled unless ready
  tabBtns.forEach(b => {
    if (loading) {
      b.disabled = true;
    } else {
      b.disabled = (b === tabResultBtn) ? !ready : false;
    }
  });
  // Update Result tab label to show progress
  if (loading) {
    tabResultBtn.textContent = 'Analyzing...';
    switchToTab(2); // move to Result view during analysis
  } else {
    tabResultBtn.textContent = 'Result';
    validateForm();
  }
}

// Render job analysis summary
function renderJobAnalysisSummary(result) {
  if (!result || typeof result !== 'object') return 'No details extracted.';
  let html = '';

  // Helper function to render a list of items with a title
  const renderSection = (title, items, isBulletList = false) => {
    if (!items || (Array.isArray(items) && items.length === 0)) return '';
    
    let content = '';
    if (Array.isArray(items)) {
      if (isBulletList) {
        content = `<ul style="margin: 0.5rem 0 1rem 1.5rem; padding: 0;">
          ${items.map(item => `<li style="margin-bottom: 0.5rem;">${item}</li>`).join('')}
        </ul>`;
      } else {
        content = `<div style="margin: 0.5rem 0 1rem 0; line-height: 1.6;">
          ${items.join('. ')}
        </div>`;
      }
    } else if (typeof items === 'object' && items !== null) {
      content = '<ul style="margin: 0.5rem 0 1rem 1.5rem; padding: 0;">';
      for (const [key, value] of Object.entries(items)) {
        if (value !== null && value !== undefined && value !== '') {
          const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          content += `<li style="margin-bottom: 0.5rem;"><strong>${label}:</strong> ${value}</li>`;
        }
      }
      content += '</ul>';
    } else if (items) {
      content = `<div style="margin: 0.5rem 0 1rem 0; line-height: 1.6;">${items}</div>`;
    }
    
    return `
      <div class="section" style="margin-bottom: 1.5rem;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 1.1rem; color: var(--primary);">
          ${title}
        </h3>
        ${content}
      </div>
    `;
  };

  // Job Title and Company
  if (result.job_title || result.company) {
    const title = [result.job_title, result.company].filter(Boolean).join(' at ');
    html += `<h2 style="margin: 0 0 1rem 0; font-size: 1.4rem;">${title}</h2>`;
  }

  // Job Description
  if (result.job_description) {
    html += renderSection('Job Description', result.job_description);
  }

  // Requirements
  const requirements = result.requirements_list || result.requirements;
  if (Array.isArray(requirements) && requirements.length) {
    html += renderSection('Requirements', requirements, true);
  }

  // Skills
  if (Array.isArray(result.skills) && result.skills.length) {
    html += renderSection('Skills', result.skills, true);
  }

  // Qualifications
  if (Array.isArray(result.qualifications) && result.qualifications.length) {
    html += renderSection('Qualifications', result.qualifications, true);
  }

  // Experience
  if (result.experience) {
    html += renderSection('Experience', result.experience);
  }

  // Responsibilities
  if (Array.isArray(result.responsibilities) && result.responsibilities.length) {
    html += renderSection('Responsibilities', result.responsibilities, true);
  }

  // Languages
  if (Array.isArray(result.languages) && result.languages.length) {
    html += renderSection('Languages', result.languages, false);
  }

  // Certifications
  if (Array.isArray(result.certifications) && result.certifications.length) {
    html += renderSection('Certifications', result.certifications, true);
  }

  // Additional sections
  const additionalSections = [
    'location', 'employment_type', 'salary', 'benefits', 
    'company_overview', 'contact_information', 'application_instructions'
  ];
  
  for (const section of additionalSections) {
    if (result[section]) {
      const title = section.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      html += renderSection(title, result[section]);
    }
  }

  return html || 'No details extracted.';
}

// Render CV analysis summary
function renderCvAnalysisSummary(result) {
  if (!result) return '';
  
  // Store the analysis for later use in the matching process
  lastCvAnalysis = result;
  
  // Extract strengths and gaps
  const strengths = Array.isArray(result?.candidate_suitability?.strengths) ? result.candidate_suitability.strengths : [];
  const gaps = Array.isArray(result?.candidate_suitability?.gaps) ? result.candidate_suitability.gaps : [];

  // Extract categorized recommendations (object format preferred)
  const recs = result?.recommendations || {};
  const tailoring = Array.isArray(recs?.tailoring) ? recs.tailoring : [];
  const interview = Array.isArray(recs?.interview_focus) ? recs.interview_focus : [];
  const career = Array.isArray(recs?.career_development) ? recs.career_development : [];

  // Helper to render a titled list (omit if empty)
  const renderList = (title, items) => {
    if (!items || !items.length) return '';
    return `
      <div class="mt-2">
        <strong>${title}</strong>
        <ul class="compact-list">${items.map(i => `<li>${UI ? UI.escapeHtml?.(String(i)) ?? String(i) : String(i)}</li>`).join('')}</ul>
      </div>
    `;
  };

  return `
    <div class="cv-analysis">
      <h3>CV Analysis Summary</h3>
      ${renderList('Strengths', strengths)}
      ${renderList('Gaps', gaps)}
      ${renderList('Tailoring Recommendations', tailoring)}
      ${renderList('Interview Focus Recommendations', interview)}
      ${renderList('Career Development Recommendations', career)}
    </div>
  `;
}
