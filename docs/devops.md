## DevOps & Environment: FFmpeg, Nginx, ENV, CORS

This guide defines the minimal ops scaffolding so uploads (~25MB) and processing run reliably across dev/stage/prod. It aligns with `agent.md` and prior agents.

### 1) System prerequisites: FFmpeg/ffprobe

- Install FFmpeg and ffprobe and ensure they are on PATH.

Ubuntu/Debian:
```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
```

Alpine (containers):
```bash
apk add --no-cache ffmpeg
```

macOS (Homebrew):
```bash
brew install ffmpeg
```

Verify installation:
```bash
ffmpeg -version | head -n 1
ffprobe -version | head -n 1
```
Expected: version line prints and exit code 0.

Runtime verification in app (logs): `records.services.verify_ffmpeg_availability()` logs availability at startup of processing.

### 2) MEDIA_ROOT layout and permissions

- Default `MEDIA_ROOT`: `<BASE_DIR>/media`

Structure:
```
media/
  voices/YYYY/MM/DD/<unique>.m4a
  notes/YYYY/MM/DD/<basename>_note.txt
```

Permissions:
- Ensure the Unix user running Django (gunicorn/dev server) has read/write/execute on `media`.
```bash
mkdir -p media/voices media/notes
chmod -R 775 media
chown -R $USER:$USER media   # or the service account
```

Free space:
- Keep at least 2× expected upload size free for temp segments during FFmpeg splitting.

### 3) Required environment variables

Set via `.env` (loaded by `python-dotenv`) or deployment environment:

- `OPENAI_API_KEY` (required): API key for Whisper transcription
- `OPENAI_BASE_URL` (optional, default `https://api.openai.com/v1`)
- `ASR_MODEL` (optional, default `whisper-1`)
- `SEGMENT_SECONDS` (optional, default `150`)
- `DEBUG` (dev=True, prod=False)
- `ALLOWED_HOSTS` (comma-separated, e.g. `example.com,api.example.com`)
- `SECRET_KEY` (set in prod)

Example: see `.env.example` in repo root.

### 4) Nginx reverse proxy (uploads up to ~25MB)

Include the following in your server/location context. This repo ships a template at `deploy/nginx/app.conf`.

```nginx
# Size: allow ~25MB uploads
client_max_body_size 25m;

# Timeouts tuned for upload + server-side processing handoff
proxy_connect_timeout 60s;
proxy_send_timeout 300s;
proxy_read_timeout 600s;  # allow processing to complete
send_timeout 300s;

# Typical reverse proxy headers
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

When proxying to gunicorn/uvicorn:
```nginx
location / {
  proxy_pass http://app:8000;
}
```

### 5) CORS policy

- Dev: open CORS
  - In settings: `CORS_ALLOW_ALL_ORIGINS = True` when `DEBUG=True`.
- Prod: restrict
  - Set `CORS_ALLOW_ALL_ORIGINS = False` and configure `CORS_ALLOWED_ORIGINS = ["https://your-flutter-web.app", "androidapp://package"]` as needed.

`django-cors-headers` is already installed and `CorsMiddleware` is before `CommonMiddleware`.

### 6) Logging configuration

- Format includes timestamps and module; default level INFO. Errors show stack traces.
- Rotation (optional): use Python `logging.handlers.RotatingFileHandler` or rely on container log rotation.

Example snippet to enable file with rotation (optional; not enabled by default):
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
        # 'file': {
        #     'class': 'logging.handlers.RotatingFileHandler',
        #     'filename': 'logs/app.log',
        #     'maxBytes': 5*1024*1024,
        #     'backupCount': 3,
        #     'formatter': 'verbose',
        # },
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
```

### 7) Optional: docker-compose (app + nginx)

The repo provides `docker-compose.yml` with two services: `app` (Django + gunicorn) and `nginx` (reverse proxy). Uses SQLite and mounts `media/`.

Run:
```bash
docker compose up -d --build
```

Smoke tests inside container:
```bash
docker compose exec app python manage.py check
docker compose exec app ffmpeg -version | head -n 1
```

### 8) Verification checklist

Commands:
```bash
python manage.py check
ffmpeg -version | head -n 1
ffprobe -version | head -n 1

# CORS (dev open): should include Access-Control-Allow-Origin: *
curl -s -D - http://localhost:8000/health/ -o /dev/null | grep -i "access-control-allow-origin" || true

# Nginx body size (~25MB): should be accepted
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  -F "audio=@test_audio.m4a" http://localhost/api/voices/
```

Expected:
- `manage.py check` passes.
- FFmpeg/ffprobe print version lines.
- CORS works per environment policy.
- Uploads up to ~25MB pass through Nginx to the app.

