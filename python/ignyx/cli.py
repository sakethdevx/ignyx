"""
Ignyx CLI — Command-line interface for Ignyx applications.
Provides dev server with hot-reload and project scaffolding.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional


def create_project(name: str) -> None:
    """
    Scaffold a production-ready Ignyx project structure.
    
    Args:
        name: The project name
    """
    project_dir = Path(name)
    
    if project_dir.exists():
        print(f"❌ Error: Directory '{name}' already exists.", file=sys.stderr)
        sys.exit(1)
    
    # Create directory structure
    directories = [
        project_dir,
        project_dir / "app",
        project_dir / "app" / "routers",
        project_dir / "app" / "models",
        project_dir / "app" / "middleware",
        project_dir / "tests",
        project_dir / "static",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "__init__.py").touch()
    
    # Create main.py
    main_content = '''"""
Main application entry point.
"""
from ignyx import Ignyx

app = Ignyx(
    title="{title}",
    version="0.1.0",
    description="A production-ready Ignyx application",
)


@app.get("/")
def root():
    """Root endpoint - Health check."""
    return {{"message": "Welcome to {title}!", "status": "operational"}}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {{"status": "healthy"}}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
'''.format(title=name.replace("_", " ").title())
    
    (project_dir / "main.py").write_text(main_content)
    
    # Create app/__init__.py with imports
    app_init_content = '''"""
Application package.
"""
from ignyx import Ignyx

__all__ = ["Ignyx"]
'''
    (project_dir / "app" / "__init__.py").write_text(app_init_content)
    
    # Create a sample router
    router_content = '''"""
Sample router module.
"""
from ignyx import Router

router = Router(prefix="/api", tags=["api"])


@router.get("/items")
def list_items():
    """List all items."""
    return {"items": []}


@router.get("/items/{item_id}")
def get_item(item_id: int):
    """Get a specific item by ID."""
    return {"item_id": item_id, "name": f"Item {item_id}"}
'''
    (project_dir / "app" / "routers" / "items.py").write_text(router_content)
    
    # Create a sample Pydantic model
    models_content = '''"""
Data models using Pydantic.
"""
try:
    from pydantic import BaseModel, Field
except ImportError:
    BaseModel = object  # type: ignore
    Field = lambda *args, **kwargs: None  # type: ignore


class Item(BaseModel):
    """Item model."""
    id: int = Field(..., description="Unique item identifier")
    name: str = Field(..., description="Item name")
    description: str = Field(default="", description="Item description")
    price: float = Field(gt=0, description="Item price")


class User(BaseModel):
    """User model."""
    id: int
    username: str
    email: str
    full_name: str = ""
'''
    (project_dir / "app" / "models" / "schemas.py").write_text(models_content)
    
    # Create sample middleware
    middleware_content = '''"""
Custom middleware.
"""
from ignyx import Middleware


class CustomMiddleware(Middleware):
    """Example custom middleware."""
    
    def __init__(self, custom_header: str = "X-Custom-Header"):
        self.custom_header = custom_header
    
    def process_request(self, request):
        """Process incoming request."""
        # Add custom processing here
        return request
    
    def process_response(self, response):
        """Process outgoing response."""
        # Add custom header to response
        if hasattr(response, "headers"):
            response.headers[self.custom_header] = "Ignyx"
        return response
'''
    (project_dir / "app" / "middleware" / "custom.py").write_text(middleware_content)
    
    # Create requirements.txt
    requirements_content = '''ignyx>=2.4.0
pydantic>=2.0.0
'''
    (project_dir / "requirements.txt").write_text(requirements_content)
    
    # Create .gitignore
    gitignore_content = '''__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.env
.venv
'''
    (project_dir / ".gitignore").write_text(gitignore_content)
    
    # Create README.md
    readme_content = f'''# {name.replace("_", " ").title()}

A production-ready Ignyx web application.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the development server:
```bash
ignyx-cli dev main.py
```

Or run directly:
```bash
python main.py
```

## Project Structure

```
{name}/
├── main.py              # Application entry point
├── app/
│   ├── routers/         # API route handlers
│   ├── models/          # Pydantic models
│   └── middleware/      # Custom middleware
├── tests/               # Test suite
├── static/              # Static files
└── requirements.txt     # Python dependencies
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Testing

Run tests with pytest:
```bash
pytest tests/
```
'''
    (project_dir / "README.md").write_text(readme_content)
    
    # Create sample test
    test_content = '''"""
Test suite for the application.
"""
from ignyx.testclient import TestClient
from main import app


def test_root_endpoint():
    """Test root endpoint."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health_check():
    """Test health check endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
'''
    (project_dir / "tests" / "test_main.py").write_text(test_content)
    
    print(f"✅ Created Ignyx project '{name}' successfully!")
    print(f"\nNext steps:")
    print(f"  cd {name}")
    print(f"  pip install -r requirements.txt")
    print(f"  ignyx-cli dev main.py")
    print(f"\n📖 Documentation: http://localhost:8000/docs")


def dev_server(target: str, host: str = "0.0.0.0", port: int = 8000) -> None:
    """
    Start the development server with hot-reload.
    
    Args:
        target: Path to the Python file containing the Ignyx app
        host: Host to bind to
        port: Port to listen on
    """
    import importlib.util
    import time
    from pathlib import Path
    
    target_path = Path(target).resolve()
    
    if not target_path.exists():
        print(f"❌ Error: File '{target}' not found.", file=sys.stderr)
        sys.exit(1)
    
    print("🔥 Ignyx Development Server")
    print(f"   📁 Watching: {target_path}")
    print(f"   🌐 Server: http://{host}:{port}")
    print(f"   🔄 Hot-reload: enabled")
    print()
    
    # Try to use watchfiles for hot-reload
    try:
        from watchfiles import run_process
        
        def run_app() -> None:
            """Load and run the app."""
            spec = importlib.util.spec_from_file_location("__main__", target_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules["__main__"] = module
                
                # Add the target directory to sys.path
                sys.path.insert(0, str(target_path.parent))
                
                spec.loader.exec_module(module)
                
                # Find the Ignyx app instance
                app = None
                for name in dir(module):
                    obj = getattr(module, name)
                    if hasattr(obj, "__class__") and obj.__class__.__name__ == "Ignyx":
                        app = obj
                        break
                
                if app:
                    app.run(host=host, port=port, reload=False)
                else:
                    print("❌ Error: No Ignyx app instance found in the target file.", file=sys.stderr)
                    sys.exit(1)
        
        # Watch for changes and reload
        watch_dir = str(target_path.parent)
        run_process(watch_dir, target=run_app, watch_filter=lambda change, path: path.endswith('.py'))
        
    except ImportError:
        print("⚠️  Warning: 'watchfiles' not installed. Hot-reload disabled.")
        print("   Install with: pip install watchfiles")
        print()
        
        # Fallback: Run without hot-reload
        spec = importlib.util.spec_from_file_location("__main__", target_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules["__main__"] = module
            
            # Add the target directory to sys.path
            sys.path.insert(0, str(target_path.parent))
            
            spec.loader.exec_module(module)
            
            # Find the Ignyx app instance
            app = None
            for name in dir(module):
                obj = getattr(module, name)
                if hasattr(obj, "__class__") and obj.__class__.__name__ == "Ignyx":
                    app = obj
                    break
            
            if app:
                app.run(host=host, port=port, reload=False)
            else:
                print("❌ Error: No Ignyx app instance found in the target file.", file=sys.stderr)
                sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="ignyx-cli",
        description="Ignyx CLI — Command-line tools for Ignyx applications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create command
    create_parser = subparsers.add_parser(
        "create",
        help="Create a new Ignyx project",
        description="Scaffold a production-ready Ignyx project structure",
    )
    create_parser.add_argument(
        "name",
        help="Project name",
    )
    
    # Dev command
    dev_parser = subparsers.add_parser(
        "dev",
        help="Start development server with hot-reload",
        description="Start the Ignyx development server with automatic reloading",
    )
    dev_parser.add_argument(
        "target",
        help="Path to the Python file containing the Ignyx app (e.g., main.py)",
    )
    dev_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    dev_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "create":
        create_project(args.name)
    elif args.command == "dev":
        dev_server(args.target, args.host, args.port)


if __name__ == "__main__":
    main()
