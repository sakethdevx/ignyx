# Deployment

Deploying an Ignyx application is straightforward because it doesn't require an external ASGI server like Uvicorn or Gunicorn. Ignyx handles its own concurrency using its high-performance Rust core powered by the Tokio runtime.

## Overview

When you run an Ignyx application, you are starting a high-performance HTTP server that manages its own threads and event loops. You simply run your Python script, and it listens on the specified port.

## Docker

Using Docker is the recommended way to deploy Ignyx for production. Here is a multi-stage build example that keeps the image small.

```dockerfile
# Use a lightweight Python base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies (ignyx requires a rust toolchain for install if not using a wheel)
# but for a production image, we usually install from pypi
RUN pip install --no-cache-dir ignyx pydantic

# Copy project files
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
```

## systemd (Linux)

You can run Ignyx as a background service on a Linux server using systemd.

**Create `/etc/systemd/system/ignyx-app.service`:**

```ini
[Unit]
Description=Ignyx API Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/my-app
Environment="PYTHONPATH=/var/www/my-app"
ExecStart=/var/www/my-app/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then enable and start it:
```bash
sudo systemctl enable ignyx-app
sudo systemctl start ignyx-app
```

## Cloud Deployment

Because Ignyx is a standard Python application that listens on a port, it works flawlessly on all modern cloud platforms.

### Railway / Render / Fly.io
Simply connect your GitHub repository. These platforms will detect your `requirements.txt` or `pyproject.toml`, install Ignyx, and run your start command (e.g., `python main.py`).

## No Uvicorn Needed

Development and production deployment of Ignyx are identical.

**fastapi_app.py:**
`uvicorn app:app` (requires external process)

**ignyx_app.py:**
`python app.py` (server is built-in)

The Rust core handles high-concurrency request parsing and dispatching far more efficiently than standard Python-based ASGI servers.
