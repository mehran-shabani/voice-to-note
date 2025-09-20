# Hand-off Log — Agent 4 (DevOps & Environment)

## Nginx config

- Location: `deploy/nginx/app.conf`
- Applied values:
  - `client_max_body_size 25m;`
  - `proxy_connect_timeout 60s;`
  - `proxy_send_timeout 300s;`
  - `proxy_read_timeout 600s;`
  - `send_timeout 300s;`
  - `proxy_pass http://app:8000;`

## Environment variable templates

- Template file: `.env.example`
- Variables:
  - `DEBUG`
  - `SECRET_KEY`
  - `ALLOWED_HOSTS`
  - `LOG_LEVEL`
  - `LOG_TO_FILE`
  - `LOG_FILE`
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`
  - `ASR_MODEL`
  - `SEGMENT_SECONDS`
  - `CORS_ALLOWED_ORIGINS`
- Loaded by: `python-dotenv` in `voicenote_backend/settings.py` (via `load_dotenv()`).

## Verification commands

Local host:
```bash
python manage.py check
ffmpeg -version | head -n 1
ffprobe -version | head -n 1
```

Docker Compose:
```bash
docker compose up -d --build
docker compose exec app python manage.py check
docker compose exec app ffmpeg -version | head -n 1
```

Nginx body size & CORS checks:
```bash
# Health check headers (dev should show permissive CORS when DEBUG=True)
curl -s -D - http://localhost/health/ -o /dev/null | grep -i "access-control-allow-origin" || true

# Upload path (replace file as needed). Expect 201 or 200.
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  -F "audio=@test_audio.m4a" http://localhost/api/voices/
```

## Notes

- `MEDIA_ROOT` is `<BASE_DIR>/media` and is created with write permissions in Dockerfile. Ensure same on host VMs.
- CORS: open in dev (`DEBUG=True`). In prod, set `CORS_ALLOWED_ORIGINS` to explicit list and `DEBUG=False`.
- Logging: default to console INFO; optional rotating file via `LOG_TO_FILE=True` and `LOG_FILE` path.

