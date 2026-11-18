# NoticeIQ

NoticeIQ is a Flask-based college notice organizer. It extracts text from PDFs, images (Tesseract OCR), and TXT files, identifies likely dates/actions, lets students review the analysis, and turns confirmed actions into tasks. Ask NoticeIQ answers from the signed-in student's saved notices only. If an AI API key is not configured, a transparent rule-based fallback is used.

## Features
- Student registration/login, password hashing, per-user data isolation
- Upload PDF/JPG/JPEG/PNG/TXT or paste notice text
- PyMuPDF PDF extraction; Pillow + Tesseract OCR for images
- Editable extracted title/category/dates/instructions and explicit task confirmation
- Task CRUD/status/filter/search, calendar, in-app notifications
- Grounded notice Q&A with optional OpenAI-compatible API and rule-based fallback
- Responsive dashboard and pages

## Local setup
1. Install Python 3.10+.
2. Install Tesseract OCR separately for image OCR:
   - Windows: install the Tesseract executable and add its install folder to PATH.
   - Ubuntu: `sudo apt-get install tesseract-ocr`
   - macOS: `brew install tesseract`
   PDF and TXT extraction do not require Tesseract.
3. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   # macOS/Linux
   source .venv/bin/activate
   ```
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and set a strong `SECRET_KEY`. Environment variables are loaded by the app when present; install `python-dotenv` if you want automatic `.env` loading, or set them in your shell.
6. Run: `python app.py`
7. Open http://127.0.0.1:5000 and register an account.

## AI configuration
Set `AI_API_KEY` and optionally `AI_MODEL` / `AI_BASE_URL`. The app sends only the current user's notice text and question to the configured OpenAI-compatible chat completions endpoint. Without a key, the built-in retrieval fallback searches the user's notice text and explicitly says when evidence is missing. Never put API keys in source control.

## Deployment on Render
1. Push this project to a Git repository.
2. Create a Render **Web Service** from the repository. Build command: `pip install -r requirements.txt`; start command: `gunicorn wsgi:app`.
3. Set environment variables: `SECRET_KEY`, `AI_API_KEY` (optional), `AI_MODEL`, `AI_BASE_URL`, and `DATABASE_URL`.
4. For production persistence, attach a Render persistent disk (for uploaded files) and set `UPLOAD_FOLDER=/var/data/uploads`.
5. Recommended production database: managed PostgreSQL; set `DATABASE_URL` to its connection string. The app normalizes `postgres://` to `postgresql://`. SQLite is suitable for local development and only for deployment when its database file is on persistent storage and there is a single app instance.
6. Set `FLASK_ENV=production`. HTTPS is provided by Render.

## Important deployment notes
- A public deployment URL can only be provided after a Render service is created and successfully deployed in an account you control. This project is deployment-ready, but no hosting account, repository, or credentials were supplied, so it has not been publicly deployed from this environment.
- Tesseract must be installed in the deployment image for image OCR. On Render, use a Docker-based deployment or a build image that installs `tesseract-ocr`; otherwise PDF/TXT processing still works and image OCR returns a clear error.
- This is a starter product, not a security audit. Add rate limiting, CSRF protection, email verification, backups, malware scanning, and operational monitoring before handling sensitive institutional documents at scale.
