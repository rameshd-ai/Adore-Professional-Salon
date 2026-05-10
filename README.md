# Glamr salon — React + FastAPI

Single-page app (Vite + React) backed by a FastAPI API. By default the API uses **SQLite** (`backend/glamr.db`). Set `DATABASE_URL` to a PostgreSQL URL for production or shared DBs. SQLAdmin is mounted at `/admin` for content management.

## Local development

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

If you use PostgreSQL, set `DATABASE_URL` (e.g. `postgresql+psycopg2://user:pass@localhost:5432/glamr`) in `.env` or the environment. Otherwise SQLite is used automatically.

On Windows PowerShell, from `backend/`, you can run `.\start-api.ps1` instead of invoking uvicorn manually.

- API: `http://127.0.0.1:8001`
- OpenAPI: `http://127.0.0.1:8001/docs`
- Admin: `http://127.0.0.1:8001/admin` (username/password from `ADMIN_USERNAME` / `ADMIN_PASSWORD`, default `admin` / `changeme`)

Local dev uses port **8001** to avoid clashing with other tools on 8000. If a port stays busy on Windows, stop the terminal that started uvicorn or use the PowerShell snippets in `CLAUDE.md`.

On first start the app creates tables and seeds demo data if tables are empty.

Uploaded gallery files are stored under `UPLOAD_DIR` (default `backend/uploads/`) and served at `/uploads/...`. In admin → Gallery, use **Upload image** and/or **Image URL**.

### Frontend

Requires Node.js **18+** (20.19+ recommended for latest Vite; this repo pins Vite 5 for broader compatibility).

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api`, `/admin`, `/uploads`, etc. to `http://127.0.0.1:8001`. Start the API on port **8001** first (see above).

To call a remote API instead, set `VITE_API_URL` (e.g. in `.env`) to the origin with no trailing slash.

**One-shot dev (Windows):** from `sal/`, run `powershell -ExecutionPolicy Bypass -File .\dev-servers.ps1` to stop anything on 8001/5173 and open two windows (API + Vite).

## Project layout

- `backend/app` — FastAPI app, models, routes under `/api`, SQLAdmin, WhatsApp webhooks under `/webhooks`
- `frontend` — React UI (Glamr styling in `src/salon.css`)
- `saul_html_free_v1.0.0` — Saul/Metronic theme assets used by the admin UI (see `backend/app/main.py`)
- Root `requirements.txt` — points to `backend/requirements.txt` (install from `backend/`)

## Production on Google Cloud (single VM)

See **[HOSTING_GCP.md](./HOSTING_GCP.md)** for Compute Engine, nginx, HTTPS, systemd, and WhatsApp webhook URL.
