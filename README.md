# PageTurn Audio

A local-first web app prototype that turns a text PDF into a multi-speaker audiobook. The app extracts PDF text, uses Qwen3.8-Flash to suggest speaker assignments, lets you review passages and voice descriptions, creates reusable Qwen Voice Design voices, then assembles generated speech into an MP3.

## Run locally

Use Python 3.10 or newer. MP3 assembly requires `ffmpeg` installed and available on `PATH`.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-web.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Add your Alibaba Cloud Model Studio **Singapore** API key to `.env` as `DASHSCOPE_API_KEY`, then start the app:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

## First audiobook workflow

1. Upload a PDF. Selectable text is extracted; image-only pages use Tesseract OCR if it is installed and available.
2. Choose **Find speakers with AI** and review the assignments. Analysis requires the Model Studio key.
3. Edit speaker names and voice descriptions, then choose **Create voice preview**. Qwen Voice Design may charge for each newly created voice; preview creation is an explicit action.
4. Assign a speaker to every passage, then choose **Generate audiobook**. Generated audio is checkpointed by passage and assembled with ffmpeg.
5. Play or download the MP3. Delete the project from the project page to remove its local files and records.

## Configuration

See `.env.example`. The defaults use the Alibaba Cloud international endpoints and model IDs `qwen3.8-flash` and `qwen3-tts-vd-2026-01-26`. The API key must be created for the Singapore region. API model names, endpoints, and deployment availability can change; adjust the settings if your Model Studio console specifies a different configuration.

The app writes projects, source PDFs, previews, audio segments, and the SQLite database under `data/` by default. Passage text is sent to Alibaba Cloud Model Studio for analysis and synthesis. This prototype has no user accounts or authentication. Run it only on a trusted local machine and keep it bound to localhost; it is not ready to expose to the internet or use as a multi-user service.

## Current boundaries

- Text-based English PDFs are the primary path. OCR currently defaults to English; install/configure Tesseract separately for scanned documents.
- Processing jobs are persisted in SQLite and resumed by the single in-process worker on restart. Run one application process only.
- Voice IDs are provider-side resources; deleting a local project does not currently delete its Model Studio voices.
- AO3 import, synchronized text highlighting, Android packaging, and manga image processing are not implemented.

The original root-level scripts are retained as experiments and are not used by this web app.
