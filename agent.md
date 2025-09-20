# Agent Execution Prompt — Minimal **VoiceNote** with Full ASR (Flutter Android + Django DRF)

> **Goal:** Flutter frontend for stable recording, minimal editing (Cut/Undo), and low‑size upload. Django backend to store the raw audio locally, split it into ≤150‑second chunks, transcribe each chunk with the official OpenAI Whisper client, merge results into a single note, and save the note file to disk. **Only file paths and metadata are stored in the database.** **Preferred API response:** `201 Created` with empty body (client should also tolerate `200 OK`).

---

## 0) Scope & Overall Flow

1. User starts recording in Flutter; supports Pause/Resume; auto‑stops at 5 minutes; saved with a unique filename.
2. In a lightweight editor the user deletes one/multiple ranges (Cut) with single‑step Undo; output is saved as a new file.
3. User taps Upload; the \~5‑minute, low‑size file is sent in a single `multipart/form-data` request to the backend.
4. Backend stores the file under `media/voices/...`, then uses FFmpeg to split it into chunks of **≤ 150 seconds**.
5. For each chunk, run ASR via OpenAI Whisper (configured through `OPENAI_BASE_URL` and `OPENAI_API_KEY`) using the Persian guidance prompt.
6. Concatenate chunk texts in order to produce one Note; write the note file under `media/notes/...`; only paths are recorded in DB.
7. API response: **prefer **``; empty body.

---

## 1) Flutter Frontend (Android)

### 1.1 Settings & Constants

```
APP_NAME = "VoiceNote"
MAX_RECORDING_MINUTES = 5
AUDIO_CONTAINER = m4a (codec AAC)
AUDIO_BITRATE_KBPS = 64 (good quality / low size)
Filename pattern: voicenote_YYYY-MM-DD_HH-mm-ss.m4a
Storage: App Scoped Storage
UPLOAD_ENDPOINT = https://<server>/api/voices/
```

> **Why M4A/AAC @ 64kbps:** excellent Android compatibility, acceptable quality, \~20MB for 5 minutes.

### 1.2 Frontend Data Models

- **RecordingMeta**: `id, localPath, fileName, createdAt, durationSec?, sizeBytes?, format`
- **EditAction**: `type=CUT, startMs, endMs, snapshotPath`
- **EditorState**: `sourceFile, pendingEdits[], hasUndo`

### 1.3 UI Components & Behavior

**Recording screen (center):**

- Start (red mic): begin recording @ 64kbps, show 5‑minute timer.
- Pause/Resume (|| ↔ ▶︎): pause/continue without producing separate files.
- Stop (■): finalize file and save locally; produce `RecordingMeta`.
- Show elapsed time and status.

**Lightweight editor (left panel):**

- Load the last file after Stop (or via "Open Last").
- Select Range + Delete (Cut); produce a temp/new version.
- One‑level Undo backed by `snapshotPath`.
- **Save Edited** → new file named `voicenote_<timestamp>_edited.m4a`.

**Upload (from editor or after recording):**

- Single `multipart/form-data` POST to `/api/voices/` with field key `audio`.
- Simple progress; **expect **``** (no body)**; also accept `200 OK`.
- (Chunked upload not required in this version.)

---

## 2) Django Backend (DRF)

### 2.1 Settings

- `INSTALLED_APPS`: `django.contrib.*`, `rest_framework`, `corsheaders`, `records`
- `MIDDLEWARE`: include `corsheaders.middleware.CorsMiddleware` **before** `CommonMiddleware`.
- `MEDIA_ROOT`: `<BASE_DIR>/media`
- `MEDIA_URL`: `/media/`
- `DEFAULT_FILE_STORAGE`: default FileSystemStorage
- `CORS`: open in development; restrict to approved app/package domains in production
- `LOGGING`: `INFO` for events, `ERROR` for exceptions
- **ENV / .env:**
  - `OPENAI_API_KEY=...`
  - `OPENAI_BASE_URL=...` (e.g., `https://api.openai.com/v1` or an alternate base)
  - `ASR_MODEL=whisper-1`
  - `SEGMENT_SECONDS=150`

> **System prerequisite:** `ffmpeg`/`ffprobe` must be installed on the server and available on `PATH`.

### 2.2 Database Models (minimal & stable)

**VoiceRecording**

- `id`: UUID (pk)
- `file`: `FileField(upload_to="voices/%Y/%m/%d/")` → stored under `media/voices/...`
- `original_name`: `CharField`
- `mime_type`: `CharField`
- `size_bytes`: `BigIntegerField`
- `duration_sec`: `IntegerField (nullable)`
- `status`: `uploaded | processing | done | failed`
- `created_at, updated_at`

**VoiceNote**

- `id`: UUID (pk)
- `voice`: `ForeignKey(VoiceRecording, on_delete=SET_NULL, null=True)`
- `file`: `FileField(upload_to="notes/%Y/%m/%d/")` → under `media/notes/...`
- `format`: `CharField (txt/md)`
- `size_bytes`: `BigIntegerField`
- `created_at, updated_at`

> **Principle:** DB stores only file paths and metadata; content stays on disk.

### 2.3 URLs & API

- `GET /health/` → `200` with `{ "status": "ok" }`
- `POST /api/voices/` (create recording & start processing)
  - **Headers:** `Content-Type: multipart/form-data`
  - **Body:** `audio=<binary>`
  - **Validation:** MIME in `audio/m4a, audio/mp4, audio/aac, audio/ogg, audio/wav`; size ≤ \~30MB

**Internal process:**

1. Safely persist file under `media/voices/...` with a unique name; create `VoiceRecording(status=uploaded)`.
2. Update `status=processing`.
3. Split via FFmpeg into chunks of ≤ `SEGMENT_SECONDS` (shorter tail covered).
4. For each chunk: ASR via official OpenAI SDK
   - Use `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `ASR_MODEL`
   - Provide the Persian domain‑guidance prompt
5. Merge transcripts in chunk order (normalize/trim whitespace & lines).
6. Write note file under `media/notes/...` as `txt` (or `md`).
7. Create related `VoiceNote` and set `VoiceRecording.status=done`.
8. Clean up temporary chunk files.

**Response:** **prefer **``, header `Location: /api/voices/{id}` (**empty body**). Minimal mode may return `200 OK`; client must accept both.

**Errors:** `400 INVALID_MIME`, `413 TOO_LARGE`, `500 PROCESSING_ERROR` ⇒ on error set `status=failed` and log.

> (Read/status endpoints are not required in this version; add later if needed.)

### 2.4 Whisper ASR Prompt (Persian guidance)

```
متن این فایل صوتی مربوط به یک جلسهٔ آموزشی به زبان فارسی است.
لطفاً واژگان را با املای رایج فارسی بنویس و اعداد را به صورت رقم ثبت کن.
نام‌های علمی و اصطلاحات را همان‌گونه که ادا می‌شود ثبت کن.
از حدس‌زدن یا افزودن کلمات خودداری کن؛ فقط آنچه گفته می‌شود را بنویس.
```

### 2.5 Service Functions (Behavior Specs)

- `store_voice_file(uploaded_file) -> VoiceRecording`

  - Extract `original_name, mime_type, size_bytes`
  - Save under `media/voices/...`; create row with `status=uploaded`

- `split_to_segments(voice_path, segment_seconds) -> List[SegmentMeta]`

  - Run FFmpeg; return an ordered list of segments with path and approx time range

- `transcribe_segment(segment_path, prompt, model, base_url, api_key) -> string`

  - Use official OpenAI client for each chunk

- `merge_transcripts(segments_text: List[str]) -> string`

  - Concatenate in order; normalize extra whitespace; ensure newline between paragraphs

- `persist_note(voice: VoiceRecording, text: string, format="txt") -> VoiceNote`

  - Write text to `media/notes/...`; create `VoiceNote` row

- `process_voice_recording(voice_id)` (main flow after upload)

  - `status=processing → split → transcribe(loop) → merge → persist_note → status=done` (or `failed`)

> **Sync vs async:** For \~5 minutes of audio, synchronous processing is acceptable. Future migration to Celery/Task Queue is possible without changing the API contract.

---

## 3) Constraints, Acceptance, and Fault Tolerance

**Acceptance:**

1. Uploading a \~5‑minute file → `` and file stored under `media/voices/...` (client can also accept `200 OK`).
2. A textual note is produced under `media/notes/...` and its path recorded in DB.
3. On errors: `status=failed` and logs contain traceable messages.

**Fault tolerance:**

- If a chunk ASR fails: retry up to 2 times; on exhaustion, insert `[SEGMENT FAILED]` in the merged text and continue.
- ASR concurrency limit: max 2–3 chunks in parallel (cost/rate friendly).
- Minimal privacy/security: no Auth; restricted CORS; remove temp files after processing.

---

## 4) Environment & DevOps Checklist

- Install `ffmpeg/ffprobe`; ensure filesystem access to `MEDIA_ROOT`.
- Env vars: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `ASR_MODEL=whisper-1`, `SEGMENT_SECONDS=150`.
- Reverse proxy (Nginx): `client_max_body_size 25m`; appropriate timeouts.
- Logging at `INFO`/`ERROR`; capture key timings (start/end, per‑segment ASR duration).

---

## 5) Sample Request/Response (for alignment)

**Request**

```
POST /api/voices/
Content-Type: multipart/form-data

form-data: audio=<binary m4a>
```

**Response (success)**

```
201 Created
Location: /api/voices/{id}

(empty body)
```

> Minimal implementations may return `200 OK`; the client must accept both.

**Response (error)**

```
400 INVALID_MIME | 413 TOO_LARGE | 500 PROCESSING_ERROR
```

---

## 6) Future Development Notes (without changing current contract)

- Extend max duration: adjust `MAX_RECORDING_MINUTES` in frontend and `client_max_body_size`/resources on server.
- Add status/output endpoints (e.g., `GET /api/voices/{id}/note`) without altering current flow.
- Enable chunked upload in client for longer audio/weak networks.
- Add a post‑ASR "writing cleanup" step using a second LLM (e.g., GPT‑4o) in a later phase.

> This document is executable by agents as‑is; all required components (models, settings, URLs, service behaviors, and flow) are defined per the request.

