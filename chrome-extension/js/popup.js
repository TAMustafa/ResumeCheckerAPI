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
const savedCvsSelect = document.getElementById('saved-cvs');
const deleteCvBtn = document.getElementById('delete-cv-btn');
const fileName = document.getElementById('file-name');
const jobDescription = document.getElementById('job-description');
const resultsSection = document.getElementById('results');
const matchScore = document.getElementById('match-score');
const overallExplanation = document.getElementById('overall-explanation');

// Results lists/chips
const strengthsList = document.getElementById('strengths-list');
const gapsList = document.getElementById('gaps-list');
const chipsMatchedSkills = document.getElementById('matched-skills');
const chipsMatchedQualifications = document.getElementById('matched-qualifications');
const chipsMatchedLanguages = document.getElementById('matched-languages');
const chipsMissing = document.getElementById('missing-requirements');
const suggestionsList = document.getElementById('suggestions-list');
// Per-category explanations
const techExplanation = document.getElementById('tech-explanation');
const expExplanation = document.getElementById('exp-explanation');
const qualExplanation = document.getElementById('qual-explanation');

// New DOM elements for individual analysis
const analyzeJobBtn = document.getElementById('analyze-job-btn');
const analyzeCvBtn = document.getElementById('analyze-cv-btn');
const jobAnalysisSummary = document.getElementById('job-analysis-summary');
const cvAnalysisSummary = document.getElementById('cv-analysis-summary');

let isAnalyzing = false;
const DEBUG = false; // local debug flag
async function loadConfig() { return API.loadConfig(); }

// Progress elements
const techSkillsProgress = document.getElementById('tech-skills-progress');
const experienceProgress = document.getElementById('experience-progress');
const qualificationsProgress = document.getElementById('qualifications-progress');
const techSkillsText = document.getElementById('tech-skills-text');
const experienceText = document.getElementById('experience-text');
const qualificationsText = document.getElementById('qualifications-text');

// State
let cvFile = null;
let jobRequirements = null;
let cvAnalysis = null;

// Store last cvAnalysis for strengths/gaps fallback
let lastCvAnalysis = null;

// Event Listeners
uploadBtn.addEventListener('click', () => cvUpload.click());
cvUpload.addEventListener('change', handleFileUpload);
savedCvsSelect.addEventListener('change', handleCvSelect);
jobDescription.addEventListener('input', validateForm);
// When job text changes, invalidate previous job analysis
jobDescription.addEventListener('input', () => { jobRequirements = null; });

// Analyze Job Description (individual)
analyzeJobBtn.addEventListener('click', async () => {
  const desc = jobDescription.value.trim();
  jobAnalysisSummary.innerHTML = '';
  if (!desc) {
    jobAnalysisSummary.textContent = 'Please enter a job description.';
    return;
  }
  analyzeJobBtn.disabled = true;
  jobAnalysisSummary.textContent = 'Analyzing...';
  try {
    const result = await analyzeJobDescription(desc);
    jobRequirements = result; // cache analyzed job requirements
    jobAnalysisSummary.innerHTML = renderJobAnalysisSummary(result);
    validateForm();
  } catch (e) {
    jobAnalysisSummary.textContent = 'Error analyzing job description.';
  }
  analyzeJobBtn.disabled = false;
});

// Analyze CV (individual)
analyzeCvBtn.addEventListener('click', async () => {
  cvAnalysisSummary.innerHTML = '';
  if (!cvFile) {
    cvAnalysisSummary.textContent = 'Please upload or select a CV.';
    return;
  }
  analyzeCvBtn.disabled = true;
  cvAnalysisSummary.textContent = 'Analyzing...';
  try {
    const result = await analyzeCV(cvFile);
    cvAnalysisSummary.innerHTML = renderCvAnalysisSummary(result);
    validateForm();
  } catch (e) {
    cvAnalysisSummary.textContent = 'Error analyzing CV.';
  }
  analyzeCvBtn.disabled = false;
});

// No Clear or Analyze buttons in Result tab anymore

document.addEventListener('DOMContentLoaded', async () => {
  await loadConfig();
  resetResults();
  validateForm();
  await fetchUploadedCVs();
  updateDeleteButtonState();
});

// Fetch list of previously uploaded CVs from the backend
async function fetchUploadedCVs() {
  try {
    const cvs = await API.fetchUploadedCVs();
    updateCvDropdown(cvs);
  } catch (error) {
    console.error('Error fetching CVs:', error);
  }
}

// Update the CV dropdown with the list of uploaded CVs
function updateCvDropdown(cvs) {
  // Clear existing options except the first one
  while (savedCvsSelect.options.length > 1) {
    savedCvsSelect.remove(1);
  }
  
  // Add new options
  cvs.forEach(cv => {
    const option = document.createElement('option');
    option.value = cv.filename;
    option.textContent = cv.originalname || cv.filename;
    savedCvsSelect.appendChild(option);
  });

  // Keep delete button state in sync
  updateDeleteButtonState();
}

// Handle CV selection from dropdown
function handleCvSelect(event) {
  const selectedCv = event.target.value;
  if (!selectedCv) return;
  
  // Reset file input
  cvUpload.value = '';
  fileName.textContent = 'Using selected CV: ' + selectedCv;
  
  // Set the cvFile to indicate a file is selected
  cvFile = { name: selectedCv, isFromDropdown: true };
  validateForm();
  resetResults();
  updateDeleteButtonState();
}

// Update the file name display when a file is selected
function handleFileUpload(event) {
  const file = event.target.files[0];
  
  // Reset dropdown selection when a new file is uploaded
  if (savedCvsSelect) {
    savedCvsSelect.selectedIndex = 0;
    updateDeleteButtonState();
  }
  
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
  } else {
    cvFile = null;
    fileName.textContent = 'No file chosen';
    lastCvAnalysis = null;
  }
  validateForm();
  resetResults();
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
  [techSkillsProgress, experienceProgress, qualificationsProgress].forEach(p => p.value = 0);
  
  techSkillsText.textContent = '0%';
  experienceText.textContent = '0%';
  qualificationsText.textContent = '0%';
  
  // Clear previous lists/chips
  if (strengthsList) strengthsList.innerHTML = '';
  if (gapsList) gapsList.innerHTML = '';
  if (chipsMatchedSkills) chipsMatchedSkills.innerHTML = '';
  if (chipsMatchedQualifications) chipsMatchedQualifications.innerHTML = '';
  if (chipsMatchedLanguages) chipsMatchedLanguages.innerHTML = '';
  if (chipsMissing) chipsMissing.innerHTML = '';
  if (suggestionsList) suggestionsList.innerHTML = '';
  if (techExplanation) techExplanation.textContent = '';
  if (expExplanation) expExplanation.textContent = '';
  if (qualExplanation) qualExplanation.textContent = '';
}

// clearAll() was unused and has been removed

// Enable/disable delete button based on selection
function updateDeleteButtonState() {
  if (!deleteCvBtn) return;
  deleteCvBtn.disabled = !savedCvsSelect || !savedCvsSelect.value;
}

// Delete selected CV
if (deleteCvBtn) {
  deleteCvBtn.addEventListener('click', async () => {
    const selected = savedCvsSelect?.value;
    if (!selected) return;

    const confirmed = confirm(`Delete "${selected}"? This cannot be undone.`);
    if (!confirmed) return;

    try {
      await API.deleteUploadedCv(selected);

      // Refresh list and UI state
      await fetchUploadedCVs();
      if (savedCvsSelect) savedCvsSelect.selectedIndex = 0;
      updateDeleteButtonState();

      // Clear file input and state
      cvUpload.value = '';
      fileName.textContent = 'No file chosen';
      cvFile = null;
      validateForm();
      resetResults();
    } catch (err) {
      console.error('Error deleting CV:', err);
      alert('Error deleting CV. Please try again.');
    }
  });
}

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
      cvAnalysis = await analyzeCV(cvFile);
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
  updateProgressBar(experienceProgress, score.experience_score);
  updateProgressBar(qualificationsProgress, score.qualifications_score);
  
  // Update score texts
  techSkillsText.textContent = `${score.technical_skills_score ?? 0}%`;
  experienceText.textContent = `${score.experience_score ?? 0}%`;
  qualificationsText.textContent = `${score.qualifications_score ?? 0}%`;

  // No summary-div to avoid duplication; chips and lists below present details

  // Populate enhanced sections using helpers (keeps Pico.css unaffected)
  if (typeof UI !== 'undefined') {
    // Strengths & gaps from CV analysis
    const strengths = UI.safeArray(cvAnalysis?.candidate_suitability?.strengths);
    const gaps = UI.safeArray(cvAnalysis?.candidate_suitability?.gaps);
    UI.setList(strengthsList, strengths);
    UI.setList(gapsList, gaps);

    // Chips for matches and missing
    UI.setChips(chipsMatchedSkills, UI.safeArray(score.matched_skills), 'blue');
    UI.setChips(chipsMatchedQualifications, UI.safeArray(score.matched_qualifications), 'green');
    UI.setChips(chipsMatchedLanguages, UI.safeArray(score.matched_languages), 'amber');
    UI.setChips(chipsMissing, UI.safeArray(score.missing_requirements), 'red');

    // Suggestions list: only use improvement_suggestions to avoid duplicating "gaps" already shown above
    const uniqueSuggestions = Array.from(new Set(
      Array.isArray(score.improvement_suggestions) ? score.improvement_suggestions : []
    ));
    UI.setList(suggestionsList, uniqueSuggestions);

    // Per-category explanations if provided by backend
    // Try multiple common keys for robustness
    if (techExplanation) techExplanation.textContent = score.technical_skills_explanation || score.technical_explanation || '';
    if (expExplanation) expExplanation.textContent = score.experience_explanation || '';
    if (qualExplanation) qualExplanation.textContent = score.qualifications_explanation || score.education_explanation || '';
  }
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
  
  // Handle both array and object formats for recommendations
  let recommendationsHtml = '';
  
  if (Array.isArray(result.recommendations) && result.recommendations.length > 0) {
    // Handle array format
    recommendationsHtml = `
      <div class="recommendations">
        <h4>Recommendations</h4>
        <ul>
          ${result.recommendations.map(rec => `<li>${rec}</li>`).join('')}
        </ul>
      </div>`;
  } else if (result.recommendations && typeof result.recommendations === 'object') {
    // Handle object format with categories
    const categories = Object.entries(result.recommendations)
      .filter(([_, recs]) => Array.isArray(recs) && recs.length > 0);
    
    if (categories.length > 0) {
      recommendationsHtml = '<div class="recommendations"><h4>Recommendations</h4>';
      categories.forEach(([category, recs]) => {
        const categoryName = category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        recommendationsHtml += `
          <div class="recommendation-category">
            <h5>${categoryName}</h5>
            <ul>
              ${recs.map(rec => `<li>${rec}</li>`).join('')}
            </ul>
          </div>`;
      });
      recommendationsHtml += '</div>';
    }
  }
  
  const html = `
    <div class="cv-analysis">
      <h3>CV Analysis Summary</h3>
      ${recommendationsHtml || '<p>No recommendations available.</p>'}
    </div>
  `;
  
  return html;
}
