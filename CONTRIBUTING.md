# Contributing to Ignyx

## Development Environment Setup
```bash
git clone <repository-url>
cd ignyx
python -m venv .venv
source .venv/bin/activate
pip install maturin pytest pydantic httpx websockets
maturin develop --release
```

## Running Tests
```bash
pytest tests/ -v
```

## Running Rust Tests
```bash
cargo test
```

## Code Style
- `cargo fmt` for Rust
- `ruff check python/` for Python

## PR Guidelines
- One feature per PR
- Tests required
- Docs required
