# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
