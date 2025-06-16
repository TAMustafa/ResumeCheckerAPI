// Tab logic
const tabBtns = [
  document.getElementById('tab-job'),
  document.getElementById('tab-cv'),
  document.getElementById('tab-result')
];
const tabSections = [
  document.getElementById('section-job'),
  document.getElementById('section-cv'),
  document.getElementById('section-result')
];

// Tab switching
tabBtns.forEach((btn, idx) => {
  btn.addEventListener('click', () => {
    tabBtns.forEach((b, i) => {
      b.classList.toggle('active', i === idx);
      b.setAttribute('aria-selected', i === idx ? 'true' : 'false');
      tabSections[i].classList.toggle('active', i === idx);
    });
  });
});

// DOM Elements (update selectors for new structure)
const cvUpload = document.getElementById('cv-upload');
const uploadBtn = document.getElementById('upload-btn');
const savedCvsSelect = document.getElementById('saved-cvs');
const fileName = document.getElementById('file-name');
const jobDescription = document.getElementById('job-description');
const analyzeBtn = document.getElementById('analyze-btn');
const spinner = document.getElementById('spinner');
const resultsSection = document.getElementById('results');
const matchScore = document.getElementById('match-score');
const overallExplanation = document.getElementById('overall-explanation');
const clearBtn = document.getElementById('clear-btn');

// New DOM elements for individual analysis
const analyzeJobBtn = document.getElementById('analyze-job-btn');
const analyzeCvBtn = document.getElementById('analyze-cv-btn');
const jobAnalysisSummary = document.getElementById('job-analysis-summary');
const cvAnalysisSummary = document.getElementById('cv-analysis-summary');

// Backend API URL - Update this to your backend URL
const API_BASE_URL = 'http://localhost:8000';

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
analyzeBtn.addEventListener('click', analyzeDocuments);

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
    jobAnalysisSummary.innerHTML = renderJobAnalysisSummary(result);
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
  } catch (e) {
    cvAnalysisSummary.textContent = 'Error analyzing CV.';
  }
  analyzeCvBtn.disabled = false;
});

// Remove old Clear button logic and use the new one in Result tab
if (clearBtn) {
  clearBtn.addEventListener('click', clearAll);
}

document.addEventListener('DOMContentLoaded', async () => {
  resetResults();
  validateForm();
  await fetchUploadedCVs();
});

// Fetch list of previously uploaded CVs from the backend
async function fetchUploadedCVs() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/uploaded-cvs`);
    if (!response.ok) throw new Error('Failed to fetch CVs');
    
    const cvs = await response.json();
    updateCvDropdown(cvs);
  } catch (error) {
    console.error('Error fetching CVs:', error);
    // Silently fail - the dropdown will just be empty
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
}

// Update the file name display when a file is selected
function handleFileUpload(event) {
  const file = event.target.files[0];
  
  // Reset dropdown selection when a new file is uploaded
  if (savedCvsSelect) {
    savedCvsSelect.selectedIndex = 0;
  }
  
  if (file && file.type === 'application/pdf') {
    cvFile = file;
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
  }
  validateForm();
  resetResults();
}

// Enable/disable analyze button based on form validity
function validateForm() {
  analyzeBtn.disabled = !(cvFile && jobDescription.value.trim());
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
  
  // Clear summary section if present
  const summaryDiv = document.getElementById('summary-div');
  if (summaryDiv) {
    summaryDiv.innerHTML = '';
  }
  if (summaryDiv) summaryDiv.remove();
}

function clearAll() {
  cvUpload.value = '';
  fileName.textContent = 'No file chosen';
  jobDescription.value = '';
  cvFile = null;
  resetResults();
  validateForm();
  // Switch to Job Vacancy tab after clearing
  tabBtns[0].click();
}

// Main function to handle document analysis
async function analyzeDocuments() {
  if (!cvFile || !jobDescription.value.trim()) return;

  try {
    setLoading(true);

    // Step 1: Analyze job description
    jobRequirements = await analyzeJobDescription(jobDescription.value);

    // Step 2: Analyze CV
    cvAnalysis = await analyzeCV(cvFile);
    lastCvAnalysis = cvAnalysis; // Save for later use

    // Step 3: Get matching score
    const score = await getMatchingScore(cvAnalysis, jobRequirements);

    // Step 4: Update UI with results
    updateResultsUI(score, cvAnalysis);

    // Show results and switch to Result tab
    resultsSection.classList.remove('hidden');
    tabBtns[2].click();
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
  try {
    console.log('Sending job description to analyze:', description);
    
    const response = await fetch(`${API_BASE_URL}/analyze-job-vacancy`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        vacancy_text: description
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Server responded with:', errorText);
      throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }
    
    const result = await response.json();
    console.log('Job analysis result:', result);
    return result;
  } catch (error) {
    console.error('Error analyzing job description:', error);
    throw error;
  }
}

// API: Analyze CV
async function analyzeCV(file) {
  const formData = new FormData();
  
  try {
    if (file.isFromDropdown) {
      // If the file is from the dropdown, we need to fetch it first
      console.log('Analyzing CV from dropdown:', file.name);
      try {
        // Ensure the filename is properly encoded for the URL
        const encodedFilename = encodeURIComponent(file.name);
        console.log('Fetching CV from:', `${API_BASE_URL}/uploaded_cvs/${encodedFilename}`);
        
        const response = await fetch(`${API_BASE_URL}/uploaded_cvs/${encodedFilename}`);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error('Server responded with:', response.status, errorText);
          throw new Error(`Failed to fetch CV: ${response.status} - ${errorText}`);
        }
        
        // Convert the response to a blob and create a File object
        const blob = await response.blob();
        if (blob.size === 0) {
          throw new Error('Received empty file from server');
        }
        
        const fetchedFile = new File([blob], file.name, { type: 'application/pdf' });
        formData.append('file', fetchedFile, file.name);
      } catch (error) {
        console.error('Error fetching CV:', error);
        throw new Error(`Error fetching CV: ${error.message}`);
      }
    } else {
      // Regular file upload
      console.log('Uploading CV file:', file.name);
      formData.append('file', file, file.name);
    }
    
    const response = await fetch(`${API_BASE_URL}/analyze-cv`, {
      method: 'POST',
      // Don't set Content-Type header - let the browser set it with the correct boundary
      headers: {
        'Accept': 'application/json'
      },
      body: formData
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('CV analysis failed. Status:', response.status, 'Response:', errorText);
      throw new Error(`CV analysis failed: ${response.status} - ${errorText}`);
    }
    
    const result = await response.json();
    console.log('CV analysis result:', result);
    return result;
  } catch (error) {
    console.error('Error analyzing CV:', error);
    throw error;
  }
}

// API: Get matching score
async function getMatchingScore(cvAnalysis, jobRequirements) {
  try {
    const response = await fetch(`${API_BASE_URL}/score-cv-match`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        cv_analysis: cvAnalysis,
        job_requirements: jobRequirements
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error getting matching score:', error);
    throw error;
  }
}

// Update the UI with the analysis results
function updateResultsUI(score, cvAnalysis) {
  // Update overall score
  // Ensure the score is a number and not hardcoded
  let overall = typeof score.overall_match_score === 'number' ? score.overall_match_score : 0;
  matchScore.textContent = `${overall}%`;
  overallExplanation.textContent = score.overall_explanation ?? 'No explanation available.';
  
  // Update progress bars
  updateProgressBar(techSkillsProgress, score.technical_skills_score);
  updateProgressBar(experienceProgress, score.experience_score);
  updateProgressBar(qualificationsProgress, score.qualifications_score);
  
  // Update score texts
  techSkillsText.textContent = `${score.technical_skills_score ?? 0}%`;
  experienceText.textContent = `${score.experience_score ?? 0}%`;
  qualificationsText.textContent = `${score.qualifications_score ?? 0}%`;

  // Show summary of matched/missing requirements if available
  let summaryDiv = document.getElementById('summary-div');
  if (!summaryDiv) {
    summaryDiv = document.createElement('div');
    summaryDiv.id = 'summary-div';
    summaryDiv.className = 'mt-2';
    resultsSection.appendChild(summaryDiv);
  }
  summaryDiv.innerHTML = '';

  function badge(label, color) {
    return `<span style="display:inline-block;background:${color};color:#fff;border-radius:12px;padding:2px 8px;margin:2px 2px 2px 0;font-size:12px;">${label}</span>`;
  }

  // Add matched skills
  if (score.matched_skills?.length) {
    summaryDiv.innerHTML += `<div class="mt-2"><strong>Matched Skills:</strong><br>${score.matched_skills.map(s => badge(s, "#1a73e8")).join('')}</div>`;
  }
  
  // Add matched qualifications
  if (score.matched_qualifications?.length) {
    summaryDiv.innerHTML += `<div class="mt-2"><strong>Matched Qualifications:</strong><br>${score.matched_qualifications.map(q => badge(q, "#43a047")).join('')}</div>`;
  }
  
  // Add missing requirements
  if (score.missing_requirements?.length) {
    summaryDiv.innerHTML += `<div class="mt-2"><strong>Missing Requirements:</strong><br>${score.missing_requirements.map(m => badge(m, "#d93025")).join('')}</div>`;
  }
  
  // Add matched languages if any
  if (score.matched_languages?.length) {
    summaryDiv.innerHTML += `<div class="mt-2"><strong>Matched Languages:</strong><br>${score.matched_languages.map(l => badge(l, "#fbbc04")).join('')}</div>`;
  }
  
  // Add any improvement suggestions
  const gaps = score.gaps ?? [];
  const suggestions = score.improvement_suggestions ?? [];
  const allSuggestions = [...gaps, ...suggestions];
  
  if (allSuggestions.length > 0) {
    const suggestionsHtml = allSuggestions.map(suggestion => 
      `<div class="suggestion">• ${suggestion}</div>`
    ).join('');
    summaryDiv.innerHTML += `<div class="mt-2"><strong>Suggestions for Improvement:</strong>${suggestionsHtml}</div>`;
  }
}

// Helper function to update a progress bar
function updateProgressBar(progressElement, percentage) {
  progressElement.value = percentage ?? 0;
  
  // For the score circle
  if (progressElement.id === 'match-score') {
    const scoreCircle = document.querySelector('.score-circle');
    if (scoreCircle) {
      scoreCircle.style.setProperty('--progress', `${percentage ?? 0}%`);
    }
  }
}

// Helper function to update a list
function updateList(listElement, items) {
  listElement.innerHTML = '';
  if (items && items.length > 0) {
    items.forEach(item => {
      const li = document.createElement('li');
      li.textContent = item;
      listElement.appendChild(li);
    });
  }
}

// Set loading state
function setLoading(isLoading) {
  if (isLoading) {
    analyzeBtn.disabled = true;
    document.querySelector('.btn-text').textContent = 'Analyzing...';
    spinner.classList.remove('hidden');
  } else {
    analyzeBtn.disabled = !(cvFile && jobDescription.value.trim().length > 0);
    document.querySelector('.btn-text').textContent = 'Analyze Match';
    spinner.classList.add('hidden');
  }
}

// Render job analysis summary
function renderJobAnalysisSummary(result) {
  if (!result || typeof result !== 'object') return 'No details extracted.';
  let html = '';

  // Helper for pills
  const pill = (text, color) =>
    `<span style="background:${color};color:#fff;border-radius:12px;padding:2px 8px;margin:2px 2px 2px 0;font-size:12px;display:inline-block;">${text}</span>`;

  // Skills
  if (Array.isArray(result.skills) && result.skills.length) {
    html += `<div><strong>Skills:</strong> ${result.skills.map(s => pill(s, "#1a73e8")).join(' ')}</div>`;
  }

  // Qualifications
  if (Array.isArray(result.qualifications) && result.qualifications.length) {
    html += `<div><strong>Qualifications:</strong> ${result.qualifications.map(q => pill(q, "#43a047")).join(' ')}</div>`;
  }

  // Requirements
  if (Array.isArray(result.requirements) && result.requirements.length) {
    html += `<div><strong>Requirements:</strong> ${result.requirements.map(r => pill(r, "#6d4cff")).join(' ')}</div>`;
  }
  if (Array.isArray(result.requirements_list) && result.requirements_list.length) {
    html += `<div><strong>Requirements:</strong> ${result.requirements_list.map(r => pill(r, "#6d4cff")).join(' ')}</div>`;
  }

  // Languages
  if (Array.isArray(result.languages) && result.languages.length) {
    html += `<div><strong>Languages:</strong> ${result.languages.map(l => pill(l, "#fbbc04")).join(' ')}</div>`;
  }

  // Experience (render as readable text if object)
  if (result.experience) {
    let exp = result.experience;
    if (typeof exp === 'object' && exp !== null) {
      // Render each key-value pair as a pill
      const expPills = Object.entries(exp)
        .filter(([k, v]) => v !== null && v !== undefined && v !== '')
        .map(([k, v]) => {
          let label = k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          return pill(`${label}: ${v}`, "#607d8b");
        })
        .join(' ');
      html += `<div><strong>Experience:</strong> ${expPills || pill('Not specified', "#bdbdbd")}</div>`;
    } else {
      html += `<div><strong>Experience:</strong> ${pill(exp, "#607d8b")}</div>`;
    }
  }

  // Responsibilities
  if (Array.isArray(result.responsibilities) && result.responsibilities.length) {
    html += `<div><strong>Responsibilities:</strong> ${result.responsibilities.map(r => pill(r, "#009688")).join(' ')}</div>`;
  }
  // Certifications
  if (Array.isArray(result.certifications) && result.certifications.length) {
    html += `<div><strong>Certifications:</strong> ${result.certifications.map(c => pill(c, "#e67c73")).join(' ')}</div>`;
  }

  return html || 'No details extracted.';
}

// Render CV analysis summary
function renderCvAnalysisSummary(result) {
  if (!result || typeof result !== 'object') return 'No details extracted.';
  let html = '';

  // Helper for pills
  const pill = (text, color) =>
    `<span style="background:${color};color:#fff;border-radius:12px;padding:2px 8px;margin:2px 2px 2px 0;font-size:12px;display:inline-block;">${text}</span>`;

  // Skills
  if (Array.isArray(result.skills) && result.skills.length) {
    html += `<div><strong>Skills:</strong> ${result.skills.map(s => pill(s, "#1a73e8")).join(' ')}</div>`;
  }

  // Qualifications
  if (Array.isArray(result.qualifications) && result.qualifications.length) {
    html += `<div><strong>Qualifications:</strong> ${result.qualifications.map(q => pill(q, "#43a047")).join(' ')}</div>`;
  }

  // Languages
  if (Array.isArray(result.languages) && result.languages.length) {
    html += `<div><strong>Languages:</strong> ${result.languages.map(l => pill(l, "#fbbc04")).join(' ')}</div>`;
  }

  // Experience (render as readable text if object)
  if (result.experience) {
    let exp = result.experience;
    if (typeof exp === 'object' && exp !== null) {
      const expPills = Object.entries(exp)
        .filter(([k, v]) => v !== null && v !== undefined && v !== '')
        .map(([k, v]) => {
          let label = k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          return pill(`${label}: ${v}`, "#607d8b");
        })
        .join(' ');
      html += `<div><strong>Experience:</strong> ${expPills || pill('Not specified', "#bdbdbd")}</div>`;
    } else {
      html += `<div><strong>Experience:</strong> ${pill(exp, "#607d8b")}</div>`;
    }
  }

  // Key Information (e.g. experience_summary)
  if (result.key_information && typeof result.key_information === 'object') {
    Object.entries(result.key_information).forEach(([k, v]) => {
      let label = k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      html += `<div><strong>${label}:</strong> ${v}</div>`;
    });
  }

  // Candidate Suitability (e.g. overall_fit_score, justification)
  if (result.candidate_suitability && typeof result.candidate_suitability === 'object') {
    if (typeof result.candidate_suitability.justification === 'string') {
      html += `<div style="margin-top:0.5rem;"><strong>Suitability:</strong> ${result.candidate_suitability.justification}</div>`;
    }
    if (typeof result.candidate_suitability.overall_fit_score !== 'undefined') {
      html += `<div><strong>Overall Fit Score:</strong> ${result.candidate_suitability.overall_fit_score}</div>`;
    }
  }

  // Recommendations (object with arrays)
  if (result.recommendations && typeof result.recommendations === 'object') {
    html += `<div style="margin-top:0.5rem;"><strong>Recommendations:</strong><ul style="margin:0.25rem 0 0 1.25rem;">`;
    Object.entries(result.recommendations).forEach(([category, recs]) => {
      if (Array.isArray(recs) && recs.length) {
        html += `<li><strong>${category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong><ul>`;
        recs.forEach(r => {
          html += `<li>${r}</li>`;
        });
        html += `</ul></li>`;
      }
    });
    html += `</ul></div>`;
  }

  // Improvement Suggestions (legacy fields)
  const suggestions = result.improvement_suggestions || result.suggestions || result.gaps;
  if (Array.isArray(suggestions) && suggestions.length) {
    html += `<div style="margin-top:0.5rem;"><strong>Suggestions for Improvement:</strong><ul style="margin:0.25rem 0 0 1.25rem;">${suggestions.map(s => `<li>${s}</li>`).join('')}</ul></div>`;
  }

  return html || 'No details extracted.';
}
