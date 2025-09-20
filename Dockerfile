FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r /workspace/requirements.txt

# App
COPY . /workspace

# Create media and logs dirs
RUN mkdir -p /workspace/media /workspace/logs && chmod -R 775 /workspace/media /workspace/logs

EXPOSE 8000

CMD ["gunicorn", "voicenote_backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]

