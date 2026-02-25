# Deployment
Ignyx handles its own concurrency via Tokio.
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install ignyx
CMD ["python", "app.py"]
```
