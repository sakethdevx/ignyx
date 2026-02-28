# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.1] - Documentation
### Added
- Full docs for dependency_injection, middleware, request, response
- New pages: testing, security, static_files, lifespan, error_handling
- Expanded docs for routing, websockets, validation, deployment
### Changed
- Updated mkdocs.yml navigation to include all pages
- Added code copy button and search suggestions to MkDocs theme

## [2.1.0] - CI/CD Improvements
### Changed
- Expanded CI matrix to Ubuntu, macOS, Windows × Python 3.12 + 3.13
- Added cargo clippy (deny warnings) to CI lint job
- Added cargo fmt --check to CI lint job
- Added ruff Python linting to CI lint job
### Added
- ruff configuration in pyproject.toml

## [1.1.1] - Test Suite Expansion & Core Fixes
### Changed
- Rewrote `conftest.py` to use `TestClient` (removed 2-second sleep antipattern)
- Switched `add_middleware` to append instead of prepend to ensure addition order matches execution order
### Added
- `test_middleware.py` — CORS, rate limiting, middleware ordering
- `test_dependencies.py` — `Depends()`, `BackgroundTask`
- `test_security.py` — OAuth2, APIKey, HTTPBasic
- `test_exceptions.py` — `HTTPException`, custom handlers
- `test_lifespan.py` — startup/shutdown, `app.state`
- `test_openapi.py` — schema generation, Swagger UI, ReDoc
- `test_static.py` — static file serving
- `pytest-cov` for coverage measurement
### Fixed
- **Pydantic Validation:** Correctly return 422 Unprocessable Entity for schema validation errors (previously 500)
- **Response Headers:** Fixed missing headers in `BaseResponse` objects and enabled merging with tuple-provided headers
- **FileResponse:** Resolved double-quoting/serialization issues with raw bytes in `FileResponse`
- **BackgroundTask:** Fixed initialization crash when passing initial tasks to the constructor
- **Dependency Injection:** Fixed `BackgroundTask` and `Request` injection into sub-dependencies
- **Static files:** Hardened path traversal protection in `StaticFiles`

## [1.1.0] - New Features
### Added
- `HTTPException` class with Rust-side status code handling
- Lifespan events: `@app.on_startup`, `@app.on_shutdown`
- `app.state` (SimpleNamespace) for app-wide data storage
- `TestClient` for testing without starting a real server
- `OAuth2PasswordBearer`, `APIKeyHeader`, `HTTPBasic` security utilities
- `RateLimitMiddleware` (sliding window, configurable requests/window)
- `AccessLogMiddleware` (method + path + status + latency)
- `StaticFiles` for serving static assets
- `app.mount()` for mounting sub-applications
### Fixed
- BackgroundTask execution no longer relies on a fixed 150ms sleep

## [1.0.6] - Code Refactoring
### Changed
- Refactored `server.rs` into maintainable modules (`handler.rs`, `websocket.rs`, `middleware.rs`, `multipart.rs`).
- Optimized `ServerState` by grouping PyObject options into `PythonCachedRefs`.
- Moved 404 fallback handling from a Python catch-all route into the Rust core.
- Cached `resolve_dependencies` directly in `HandlerSignature`.

## [1.0.5] - README Rewrite
### Changed
- Complete README rewrite with full benchmark table
- Added pepy.tech download badge
- Added feature comparison table vs FastAPI
- Added current limitations section
- Added collapsible feature examples

## [1.0.4] - Repository Structure
### Added
- CONTRIBUTING.md with dev setup guide
- CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- SECURITY.md with vulnerability reporting process
- GitHub issue templates (bug report, feature request)
- GitHub PR template
- docs.yml workflow for auto-deploying MkDocs to GitHub Pages
- static/swagger-ui.html for self-hosted API docs
- 6 new example files in examples/
- benchmarks/results/ directory

### Removed
- benchmarks/test_loop.py, test_thread_local.py, test_threadsafe.py
 (test utilities moved to dev notes, not part of benchmark suite)

## [1.0.3] - Unreleased

### Added
- **PEP 561 Compliance:** Added `py.typed` marker to enable strict type-checking in external projects.
- **Type Hints:** Added comprehensive type annotations to core Python components (`app.py`, `router.py`, `responses.py`) to drastically improve developer experience in modern IDEs like VS Code and PyCharm.
- **Documentation:** Added professional, PEP-257 compliant docstrings to all major classes and methods (e.g., `Router`, `JSONResponse`, `FileResponse`).

### Changed
- Refactored `__version__` export in python module to accurately reflect Rust crate versions.
- Updated default `server` headers globally from `Ignyx/0.1.0` to `Ignyx/1.0.0` making HTTP response metadata accurate.
- Promoted PyPI classifier from `Development Status :: 3 - Alpha` to `Development Status :: 5 - Production/Stable`.
- Added `Framework :: AsyncIO` PyPI classifier for exact framework precision.

### Fixed
- Fixed internal typing inconsistencies and missing arguments traversing the Rust-Python barrier.
