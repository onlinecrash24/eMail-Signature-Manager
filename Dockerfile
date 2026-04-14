FROM python:3.12-slim

WORKDIR /opt/signature-tool

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Verify files are present during build
RUN python -c "from app import create_app; print('BUILD: Import OK')"

# Create data directories
RUN mkdir -p /opt/signature-tool/data/generated /opt/signature-tool/data/uploads

# Make entrypoint executable
RUN chmod +x entrypoint.sh

ENV FLASK_APP=run.py
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LISTEN_PORT=5010

EXPOSE 5010

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import os; import urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"LISTEN_PORT\",\"5010\")}/auth/login')" || exit 1

CMD ["./entrypoint.sh"]
