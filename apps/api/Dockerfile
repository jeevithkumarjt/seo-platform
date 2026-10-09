FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 60 -r requirements.txt
COPY src ./src
ENV PYTHONPATH=/app/src
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
