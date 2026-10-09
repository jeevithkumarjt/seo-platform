FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 60 -r requirements.txt
RUN python -m playwright install --with-deps chromium firefox webkit || echo "playwright browser install deferred"
COPY src ./src
ENV PYTHONPATH=/app/src
CMD ["celery", "-A", "worker_app", "worker", "--loglevel=info", "--concurrency=2", "-B"]
