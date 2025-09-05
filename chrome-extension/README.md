# Resume Checker Chrome Extension

This folder contains the Chrome extension UI that talks to the FastAPI backend.

## Features

- Upload CV (PDF) and analyze it
- Analyze job description
- Score match between CV and job requirements
- Uses the user-provided OpenAI API key (stored locally by default)

## Requirements

- Google Chrome (or Chromium-based browser)
- Backend API reachable at your domain
  - Current production domain: `http://cv.kroete.io` (HTTP, no SSL yet)
  - Local development (optional): `http://localhost:8000`

## Configuration

The extension reads a base API URL and your LLM API key.

- Base URL default is `http://cv.kroete.io`. You can override it in Options if needed.
- Provide your OpenAI API key in the Options page. The key is stored in `chrome.storage.local` by default.

### Permissions and CSP

- `manifest.json` includes `host_permissions` for:
  - `http://cv.kroete.io/*`
  - `http://cv.kroete.io:8000/*` (for dev scenarios)
  - `http://localhost:8000/*` (local dev)
- Content Security Policy allows `connect-src` to the above origins.

If you later move to HTTPS, you will need to update the URLs to `https://cv.kroete.io` in:
- `manifest.json` (`connect-src` and `host_permissions`)
- `js/api.js` (default base URL)
- `js/options.js` (default base URL)

## Load the Extension (Unpacked)

1. Open `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `chrome-extension/` directory
5. Click "Reload" whenever you make changes to the extension files

## Using the Extension

- Click the extension icon to open the popup
- Go to the settings (gear icon) to set your OpenAI API key
- Optionally, change the base URL if you want to point to a different backend
- Analyze a job description and upload/select a CV
- View the results and suggestions

## Testing

End-to-end tests live in the `e2e/` folder and use Playwright.

- From `e2e/` directory: `npm test`
- The tests mock network requests and the Chrome APIs used by the extension

## Privacy

- The provided API key is stored locally by default (optionally mirrored to Chrome sync if you opt in)
- CV PDFs are uploaded to the backend only for analysis. A server setting controls retention. By default, uploaded CVs are not retained unless explicitly enabled.

## Troubleshooting

- If you see connection errors, confirm the backend is reachable at `http://cv.kroete.io/healthz`
- Ensure your DNS A/AAAA records point to the server
- After changing `manifest.json`, reload the extension from `chrome://extensions`
