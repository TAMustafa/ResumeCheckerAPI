import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

// Helper to build file:// URL to popup.html
function popupFileUrl(): string {
  const popupPath = path.resolve(__dirname, '../../chrome-extension/popup.html');
  return 'file://' + popupPath.replace(/\\/g, '/');
}

// Helper to build file:// URL to options.html
function optionsFileUrl(): string {
  const optPath = path.resolve(__dirname, '../../chrome-extension/options.html');
  return 'file://' + optPath.replace(/\\/g, '/');
}

test.describe('Popup UI (mocked backend, mocked chrome APIs)', () => {
  test('renders results sections with mocked data (no duplication)', async ({ page }) => {
    // Mock chrome.* APIs used by the extension
    await page.addInitScript(() => {
      // Minimal mock for chrome.storage APIs used in code
      // Keys stored in-memory for test
      const store: Record<string, any> = {
        llmProvider: 'openai',
        llmKeys: { openai: 'test-key' },
        llmModels: { openai: 'gpt-4o' },
        syncKeysOptIn: false,
      };
      // @ts-ignore
      window.chrome = {
        runtime: {
          openOptionsPage: () => {},
        },
        storage: {
          local: {
            get: (keys: any, cb: any) => cb(store),
            set: (obj: any, cb: any) => { Object.assign(store, obj); cb && cb(); },
          },
          sync: {
            get: (_keys: any, cb: any) => cb({}),
            set: (_obj: any, cb: any) => cb && cb(),
          },
        },
      } as any;
    });

    // Mock backend endpoints used by the UI flow
    await page.route('**/analyze-job-vacancy', async route => {
      const json = {
        job_title: 'Frontend Engineer',
        technical_requirements: ['JavaScript', 'React'],
        required_experience: ['3+ years UI dev'],
        preferred_qualifications: ['BSc CS'],
        languages: ['English'],
      };
      await route.fulfill({ json });
    });
    await page.route('**/analyze-cv', async route => {
      const json = {
        candidate_suitability: {
          strengths: ['Strong React experience'],
          gaps: ['No TypeScript'],
        },
      };
      await route.fulfill({ json });
    });
    await page.route('**/score-cv-match', async route => {
      const json = {
        overall_score: 78,
        overall_explanation: 'Good match',
        technical_skills_score: 80,
        experience_score: 70,
        qualifications_score: 60,
        matched_skills: ['React', 'JavaScript'],
        matched_qualifications: ['BSc CS'],
        matched_languages: ['English'],
        missing_requirements: ['TypeScript'],
        improvement_suggestions: ['Learn TypeScript'],
      };
      await route.fulfill({ json });
    });

    // Navigate to popup.html as a file (not as a chrome extension)
    await page.goto(popupFileUrl());

    // Fill job description
    await page.fill('#job-description', 'We need a frontend engineer with React');

    // Mock a file upload input by creating a temporary minimal PDF buffer
    const tmpPdfPath = path.join(process.cwd(), 'tmp-test.pdf');
    fs.writeFileSync(tmpPdfPath, '%PDF-1.4\n%\xE2\xE3\xCF\xD3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF');
    await page.setInputFiles('#cv-upload', tmpPdfPath);

    // Click Analyze Job first, then switch to CV tab; CV analysis happens automatically after upload
    await page.click('#analyze-job-btn');
    await page.click('#tab-cv');
    // Wait for auto CV analysis to reflect in summary
    await expect(page.locator('#cv-analysis-summary')).toContainText('CV Analysis');

    // Open Result tab to trigger combined scoring and rendering
    await page.click('#tab-result');
    // Expect results rendered
    await expect(page.locator('#match-score')).toBeVisible();
    await expect(page.locator('#strengths-list li')).toHaveCount(1);
    await expect(page.locator('#gaps-list li')).toHaveCount(1);
    await expect(page.locator('#suggestions-list li')).toHaveCount(1);

    // Ensure no duplication: suggestion should not equal gap text
    const gapText = await page.locator('#gaps-list li').first().textContent();
    const suggestionText = await page.locator('#suggestions-list li').first().textContent();
    expect(gapText && suggestionText && suggestionText.includes(gapText)).toBeFalsy();

    // Cleanup
    fs.unlinkSync(tmpPdfPath);
  });
});

// Purge/retention functionality removed; no options purge test
