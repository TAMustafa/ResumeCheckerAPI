// UI helper utilities for popup rendering
// Pico-friendly: we only add small utility classes and avoid overriding Pico tokens.
(function initUIHelpers(global) {
  function safeArray(x) {
    return Array.isArray(x) ? x : [];
  }

  // Detailed sections
  function renderJobDetails(job) {
    if (!job || typeof job !== 'object') return '';
    const sections = [];
    // Requirements list (common names in backend models)
    const reqs = job.requirements_list || job.requirements;
    if (Array.isArray(reqs) && reqs.length) sections.push(renderListSection('Requirements', reqs));

    // Skills
    const tech = safeArray(job?.required_skills?.technical);
    if (tech.length) sections.push(renderChipsSection('Technical Skills', tech));
    const soft = safeArray(job?.required_skills?.soft);
    if (soft.length) sections.push(renderChipsSection('Soft Skills', soft));

    // Experience (object or string)
    if (job.experience) sections.push(renderGenericSection('Experience', job.experience));

    // Qualifications
    if (Array.isArray(job.qualifications) && job.qualifications.length) sections.push(renderListSection('Qualifications', job.qualifications));

    // Responsibilities
    if (Array.isArray(job.responsibilities) && job.responsibilities.length) sections.push(renderListSection('Responsibilities', job.responsibilities));

    // Languages
    const langs = safeArray(job.languages);
    if (langs.length) sections.push(renderChipsSection('Languages', langs));

    // Certifications
    const certs = safeArray(job.certifications);
    if (certs.length) sections.push(renderListSection('Certifications', certs));

    // Additional fields
    const additional = ['location', 'employment_type', 'salary', 'benefits', 'company_overview', 'contact_information', 'application_instructions'];
    additional.forEach((k) => {
      if (job[k]) sections.push(renderGenericSection(toTitle(k), job[k]));
    });
    return sections.join('');
  }

  function renderCvDetails(cv) {
    if (!cv || typeof cv !== 'object') return '';
    const sections = [];
    const ki = cv.key_information || {};
    const cs = cv.candidate_suitability || {};

    // Experience summary and years
    if (ki.experience_summary) sections.push(renderGenericSection('Experience Summary', ki.experience_summary));
    if (typeof ki.years_of_experience === 'number') sections.push(renderGenericSection('Years of Experience', `${ki.years_of_experience}`));

    // Skills
    const tech = safeArray(ki.technical_skills);
    if (tech.length) sections.push(renderChipsSection('Technical Skills', tech));
    const soft = safeArray(ki.soft_skills);
    if (soft.length) sections.push(renderChipsSection('Soft Skills', soft));

    // Education and certifications
    const education = safeArray(ki.education);
    if (education.length) sections.push(renderListSection('Education', education));
    const certs = safeArray(ki.certifications);
    if (certs.length) sections.push(renderListSection('Certifications', certs));

    // Languages
    const langs = safeArray(ki.languages);
    if (langs.length) sections.push(renderChipsSection('Languages', langs));

    // Projects or accomplishments if provided
    const projects = safeArray(ki.projects || cv.projects);
    if (projects.length) sections.push(renderListSection('Projects', projects));

    // Suitability strengths and gaps
    const strengths = safeArray(cs.strengths);
    if (strengths.length) sections.push(renderListSection('Strengths', strengths));
    const gaps = safeArray(cs.gaps);
    if (gaps.length) sections.push(renderListSection('Gaps', gaps));

    // Recommendations (array or object)
    if (Array.isArray(cv.recommendations)) {
      if (cv.recommendations.length) sections.push(renderListSection('Recommendations', cv.recommendations));
    } else if (cv.recommendations && typeof cv.recommendations === 'object') {
      const cats = Object.entries(cv.recommendations).filter(([, arr]) => Array.isArray(arr) && arr.length);
      cats.forEach(([cat, arr]) => sections.push(renderListSection(`${toTitle(cat)} Recommendations`, arr)));
    }
    return sections.join('');
  }

  // Internal small render helpers (use Pico-friendly markup)
  function renderListSection(title, items) {
    return `
      <div style="margin-top:0.5rem;">
        <strong>${escapeHtml(title)}</strong>
        <ul class="compact-list">${items.map((i) => `<li>${escapeHtml(String(i))}</li>`).join('')}</ul>
      </div>`;
  }
  function renderChipsSection(title, items) {
    return `
      <div style="margin-top:0.5rem;">
        <strong>${escapeHtml(title)}</strong>
        <div class="chips">${items.map((i) => `<span class="chip blue">${escapeHtml(String(i))}</span>`).join('')}</div>
      </div>`;
  }
  function renderGenericSection(title, content) {
    const body = Array.isArray(content)
      ? content.map((c) => `<div>${escapeHtml(String(c))}</div>`).join('')
      : escapeHtml(String(content));
    return `
      <div style="margin-top:0.5rem;">
        <strong>${escapeHtml(title)}</strong>
        <div>${body}</div>
      </div>`;
  }
  function toTitle(s) { return String(s).replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase()); }

  function setList(ulEl, items) {
    if (!ulEl) return;
    ulEl.innerHTML = items.length ? items.map(i => `<li>${escapeHtml(String(i))}</li>`).join('') : '';
  }

  function setChips(container, items, color) {
    if (!container) return;
    container.innerHTML = items
      .map(i => `<span class="chip ${color}">${escapeHtml(String(i))}</span>`)
      .join('');
  }

  function renderJobOverview(job) {
    if (!job || typeof job !== 'object') return '<p class="secondary">No job details.</p>';
    const parts = [];
    if (job.job_title || job.company) parts.push(`<strong>${[job.job_title, job.company].filter(Boolean).map(escapeHtml).join(' at ')}</strong>`);
    if (job.seniority_level) parts.push(`Seniority: ${escapeHtml(job.seniority_level)}`);
    const minYears = job?.experience?.minimum_years;
    if (typeof minYears === 'number') parts.push(`Min Experience: ${minYears} yrs`);
    const tech = safeArray(job?.required_skills?.technical).slice(0, 6).map(escapeHtml).join(', ');
    if (tech) parts.push(`Technical: ${tech}`);
    const soft = safeArray(job?.required_skills?.soft).slice(0, 6).map(escapeHtml).join(', ');
    if (soft) parts.push(`Soft: ${soft}`);
    const langs = safeArray(job?.languages).slice(0, 5).map(escapeHtml).join(', ');
    if (langs) parts.push(`Languages: ${langs}`);
    return `<p>${parts.join('<br>')}</p>`;
  }

  function renderCvOverview(cv) {
    if (!cv || typeof cv !== 'object') return '<p class="secondary">No CV details.</p>';
    const lines = [];
    const fit = cv?.candidate_suitability?.overall_fit_score;
    if (typeof fit === 'number') lines.push(`Overall Fit: ${fit}/10`);
    const expSummary = cv?.key_information?.experience_summary;
    if (expSummary) lines.push(`Experience: ${escapeHtml(expSummary)}`);
    const tech = safeArray(cv?.key_information?.technical_skills).slice(0, 6).map(escapeHtml).join(', ');
    if (tech) lines.push(`Technical: ${tech}`);
    const soft = safeArray(cv?.key_information?.soft_skills).slice(0, 6).map(escapeHtml).join(', ');
    if (soft) lines.push(`Soft: ${soft}`);
    const certs = safeArray(cv?.key_information?.certifications).slice(0, 4).map(escapeHtml).join(', ');
    if (certs) lines.push(`Certifications: ${certs}`);
    const langs = safeArray(cv?.key_information?.languages).slice(0, 5).map(escapeHtml).join(', ');
    if (langs) lines.push(`Languages: ${langs}`);
    return `<p>${lines.join('<br>')}</p>`;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  global.UI = { safeArray, setList, setChips, renderJobOverview, renderCvOverview, renderJobDetails, renderCvDetails };
})(window);
