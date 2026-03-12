# Changelog

All notable changes to SignBridge Live will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- ReactJS frontend with TypeScript
- Python FastAPI backend
- WebSocket support for real-time communication
- 3D avatar rendering with Three.js
- Audio capture and playback hooks
- Complete documentation (11 guides)
- Docker and Docker Compose setup
- Development environment configuration

### Changed

### Deprecated

### Removed

### Fixed

### Security

---

## [0.1.0] - 2025-03-05

### Added
- Initial project setup with React + FastAPI
- Frontend: React 18, TypeScript, Vite, Three.js
- Backend: FastAPI, WebSocket, Google Cloud ready
- Documentation: 11 comprehensive guides
- Docker setup with multi-service orchestration
- Development environment with hot reload
- API client with Axios
- Custom React hooks for:
  - WebSocket management
  - Audio capture (Microphone)
  - Audio playback (AudioContext)
  - Avatar rendering (Three.js)
  - Conversation state
- ESLint and Prettier configuration
- Type definitions for all components
- Environment variable templates (.env.example)

### Infrastructure
- Docker Compose for local development
- Dockerfile for both frontend and backend
- Configuration for Vite proxy (WebSocket/API)
- TypeScript configuration for strict type checking
- ESLint and Prettier for code quality

### Documentation
- README.md - Project overview
- BUILD.md - Build and setup guide
- DEPLOYMENT.md - Production deployment guide
- DEVOPS.md - DevOps and infrastructure
- TESTING.md - Testing strategy and examples
- CONTRIBUTING.md - Contribution guidelines
- ARCHITECTURE.md - System architecture
- QUICK_REFERENCE.md - Command reference
- PROJECT_SUMMARY.md - Project overview
- INDEX.md - Documentation index
- project-details.MD - Full specification

---

## Version Numbering

- **MAJOR** version when you make incompatible API changes
- **MINOR** version when you add functionality in a backwards compatible manner
- **PATCH** version when you make backwards compatible bug fixes

Example: v1.2.3 (MAJOR.MINOR.PATCH)

---

## Release Process

1. Update version in `package.json` (frontend) and `requirements.txt` (backend)
2. Update CHANGELOG.md with all changes
3. Commit: `git commit -m "chore: release v1.2.3"`
4. Tag: `git tag -a v1.2.3 -m "Release version 1.2.3"`
5. Push: `git push origin main && git push origin v1.2.3`
6. Create GitHub Release with CHANGELOG entry

---

## Categories

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for security issue fixes

---

## Dates

Use YYYY-MM-DD format for dates (e.g., 2025-03-05)

---

## Links

Provide links to related issues and pull requests:
- Issue: [#123]
- PR: [#456]
- Comparison: [v0.1.0...v0.2.0]

---

## Keep It Human

Write changelog entries that are:
- Clear and concise
- User-focused (what changed for users)
- Grouped logically
- Timestamped
- Linked to PRs/issues

---

## Sample Entry

```markdown
## [1.0.0] - 2025-04-01

### Added
- Session persistence with Redis ([#100])
- Real-time participant list in UI ([#101])
- Audio quality selection in settings ([#102])

### Changed
- Improved WebSocket reconnection logic ([#103])
- Updated Gemini model to latest version ([#104])

### Fixed
- Fixed avatar animation sync issue ([#105])
- Corrected transcript display truncation ([#106])

### Security
- Added input validation for all API endpoints ([#107])
- Implemented rate limiting on WebSocket ([#108])
```

---

## Links to Versions

[Unreleased]: https://github.com/your-org/signbridge/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/signbridge/releases/tag/v0.1.0
