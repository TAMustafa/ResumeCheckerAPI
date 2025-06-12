// DOM Elements
const cvUpload = document.getElementById('cv-upload');
const fileName = document.getElementById('file-name');
const jobDescription = document.getElementById('job-description');
const analyzeBtn = document.getElementById('analyze-btn');
const spinner = document.getElementById('spinner');
const resultsSection = document.getElementById('results');
const matchScore = document.getElementById('match-score');
const overallExplanation = document.getElementById('overall-explanation');

// Progress elements
const techSkillsProgress = document.getElementById('tech-skills-progress');
const experienceProgress = document.getElementById('experience-progress');
const qualificationsProgress = document.getElementById('qualifications-progress');
const techSkillsText = document.getElementById('tech-skills-text');
const experienceText = document.getElementById('experience-text');
const qualificationsText = document.getElementById('qualifications-text');

// List elements
const strengthsList = document.getElementById('strengths-list');
const improvementsList = document.getElementById('improvements-list');
const recommendationsList = document.getElementById('recommendations-list');

// State
let cvFile = null;
let jobRequirements = null;
let cvAnalysis = null;

// Backend API URL - Update this to your backend URL
const API_BASE_URL = 'http://localhost:8000';

// Event Listeners
cvUpload.addEventListener('change', handleFileUpload);
jobDescription.addEventListener('input', validateForm);
analyzeBtn.addEventListener('click', analyzeDocuments);

// Update the file name display when a file is selected
function handleFileUpload(event) {
  const file = event.target.files[0];
  if (file) {
    if (file.type === 'application/pdf') {
      cvFile = file;
      fileName.textContent = file.name;
      validateForm();
    } else {
      alert('Please upload a PDF file');
      cvUpload.value = '';
      fileName.textContent = 'No file chosen';
    }
  }
}

// Enable/disable analyze button based on form validity
function validateForm() {
  analyzeBtn.disabled = !(cvFile && jobDescription.value.trim().length > 0);
}

// Main function to handle document analysis
async function analyzeDocuments() {
  if (!cvFile || !jobDescription.value.trim()) return;

  try {
    // Show loading state
    setLoading(true);
    
    // Step 1: Analyze job description
    jobRequirements = await analyzeJobDescription(jobDescription.value);
    
    // Step 2: Analyze CV
    cvAnalysis = await analyzeCV(cvFile);
    
    // Step 3: Get matching score
    const score = await getMatchingScore(cvAnalysis, jobRequirements);
    
    // Step 4: Update UI with results
    updateResultsUI(score);
    
    // Show results
    resultsSection.classList.remove('hidden');
  } catch (error) {
    console.error('Error analyzing documents:', error);
    alert('An error occurred while analyzing the documents. Please try again.');
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
  formData.append('file', file, file.name);
  
  try {
    console.log('Uploading CV file:', file.name);
    
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
function updateResultsUI(score) {
  // Update overall score
  matchScore.textContent = `${score.overall_match_score}%`;
  overallExplanation.textContent = score.overall_explanation || 'No explanation available.';
  
  // Update progress bars
  updateProgressBar(techSkillsProgress, score.technical_skills_score);
  updateProgressBar(experienceProgress, score.experience_score);
  updateProgressBar(qualificationsProgress, score.qualifications_score);
  
  // Update score texts
  techSkillsText.textContent = `${score.technical_skills_score}%`;
  experienceText.textContent = `${score.experience_score}%`;
  qualificationsText.textContent = `${score.qualifications_score}%`;
  
  // Update lists
  updateList(strengthsList, score.strengths || ['No strengths identified.']);
  updateList(improvementsList, score.gaps || ['No specific areas for improvement identified.']);
  updateList(recommendationsList, score.improvement_suggestions || ['No specific recommendations available.']);
}

// Helper function to update a progress bar
function updateProgressBar(progressElement, percentage) {
  progressElement.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
}

// Helper function to update a list
function updateList(listElement, items) {
  listElement.innerHTML = '';
  items.forEach(item => {
    const li = document.createElement('li');
    li.textContent = item;
    listElement.appendChild(li);
  });
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
