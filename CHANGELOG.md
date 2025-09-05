# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning where practical.

## [Unreleased]
- TBD

## [0.2.0] - 2025-09-05
### Added
- Chrome extension README with setup, permissions/CSP, and testing instructions (`chrome-extension/README.md`).
- "SSL Migration (HTTP -> HTTPS)" section to backend docs with exact file paths and steps (`backend/README.md`).

### Changed
- Production domain switched from Hetzner IP to `http://cv.kroete.io` (HTTP, no SSL currently).
- Default API base URL in extension:
  - `chrome-extension/js/api.js` now defaults to `http://cv.kroete.io`.
  - `chrome-extension/js/options.js` default fallback updated to `http://cv.kroete.io`.
- Manifest CSP and permissions updated:
  - `chrome-extension/manifest.json` `connect-src` and `host_permissions` updated to allow `http://cv.kroete.io` and `http://cv.kroete.io:8000`.
- Backend CORS defaults updated:
  - `backend/app.py` `ALLOWED_ORIGINS` default now includes `http://cv.kroete.io`.
- E2E tests updated to reflect domain change (`e2e/tests/ui.spec.ts`).
- Backend documentation updated to reflect new domain and ALLOWED_ORIGINS examples (`backend/README.md`, `backend/quick_reference.md`).

### Notes
- When migrating to HTTPS later, update the following to `https://cv.kroete.io`:
  - `backend/app.py` CORS allowed origins (or set via `ALLOWED_ORIGINS` env)
  - `chrome-extension/manifest.json` `connect-src` and `host_permissions`
  - `chrome-extension/js/api.js` and `chrome-extension/js/options.js` defaults
  - Set `DOMAIN=cv.kroete.io` for Caddy if using the provided config

## [0.1.0] - 2025-08-XX
- Initial public version with FastAPI backend, Chrome extension UI, and basic e2e tests.
