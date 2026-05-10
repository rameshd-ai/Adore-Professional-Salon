# Glamr / salon — AI context (read first)

Use this file to avoid re-explaining the repo. **Prefer editing only files listed below** unless the task clearly needs more.

## Stack

- **Backend:** FastAPI (`backend/app/main.py`), SQLAlchemy 2, SQLAdmin on `/admin`. Production React bundle from `frontend/dist` is served at **`/`** (same port as `/api` after `npm run build`). Bundled catalog images mount at **`/site-media`** (files under `backend/site_media/`; refresh via `python scripts/fetch_site_media.py` from `backend/`).
- **Custom admin:** `GlamrAdmin` (`backend/app/admin_patch.py`) — session-safe uploads, `ajax_lookup` (blank `term` → empty results; single `form_ajax_ref` → infer `name` if missing).
- **Theme:** Saul/Metronic assets under `/saul-admin`; admin bridge CSS `/admin-theme/sqladmin-saul-bridge.css`.
- **Fix script:** `/admin-theme/sqladmin-select2-ajax-fix.js` — **must load after** sqladmin `main.js` (stock Select2 `ajax.data` loses `name` → 400). Declared in `backend/templates/sqladmin/base.html`.

## Run (dev)

**Single server (recommended):** build the React app once, then only uvicorn serves the public site, REST API, and SQLAdmin.

```text
cd frontend
npm run build
cd ../backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

- Public site: `http://127.0.0.1:8001/`
- API: `http://127.0.0.1:8001/api/...`
- Admin: `http://127.0.0.1:8001/admin`
- Docs: `/docs`

Or from `sal/`: `powershell -NoProfile -ExecutionPolicy Bypass -File .\dev-servers.ps1` (runs `npm run build` then starts API).

Default DB is **SQLite** at `backend/glamr.db` (see `app/config.py`). Override with `DATABASE_URL` for PostgreSQL.

Optional **`SPA_DIST`** / `spa_dist` in `.env`: absolute path to Vite `dist` when it is not `sal/frontend/dist`.

**Port:** **8001** is the default app port (not 8000). With single-server mode the browser uses the same origin; no `VITE_API_URL` needed.

### Stop backend (Windows / PowerShell)

`uvicorn --reload` runs a **supervisor + worker** processes; killing “whatever is on the port” once may miss a child. Prefer one of:

```powershell
# By port (8000 and 8001 — adjust if you only use one)
Get-NetTCPConnection -LocalPort 8000,8001 -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
```

```powershell
# All Python processes whose command line mentions uvicorn
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
  Where-Object { $_.CommandLine -match 'uvicorn' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Do **not** use `foreach ($pid in ...)` — `$PID` is reserved in PowerShell and breaks the loop.

**Still active?** Close the terminal that started uvicorn, or use `taskkill` / the port-kill snippets above from a normal PowerShell window. If Windows shows a “ghost” listener on a port, rebooting or resetting WinNAT (admin) sometimes clears it.

### Frontend dev server (optional)

```text
cd frontend
npm run dev
```

Hot reload at `http://127.0.0.1:5173` — Vite proxies `/api`, `/admin`, `/uploads`, `/site-media`, `/admin-theme`, `/saul-admin` to **8001** (`frontend/vite.config.js`). Use when editing React often.

**All-in-one (Windows):** `sal/dev-servers.ps1` builds the SPA then starts API only (single origin on **8001**). Pass **`-WithVite`** for API + Vite in two windows (legacy).

## High-value paths

| Area | Path |
|------|------|
| Models | `backend/app/models.py` |
| Admin views | `backend/app/admin_views.py` |
| Admin mount + auth | `backend/app/admin_setup.py` |
| API routes | `backend/app/routers.py` |
| Config | `backend/app/config.py` |
| Visit pricing helpers | `backend/app/visit_pricing.py` |
| Bundled image URLs + DB migration from remotes | `backend/app/site_media.py`, `backend/scripts/fetch_site_media.py` |
| SQLAdmin templates (overrides) | `backend/templates/sqladmin/` |

## Service visits (Customers → Service history)

- **Customer** search: AJAX by **phone** only (`form_ajax_refs` fields `("phone",)`).
- **`form_ajax_refs` `order_by`:** use **`[Customer.id]`** (list of columns). **Never** `("id",)` — SQLAlchemy 2 breaks `ORDER BY`.
- **New customer:** phone alone is enough; empty name → stored as `Walk-in`. Merge in `_visit_merge_new_customer`.
- **Menu lines:** M2M `visit_menu_items` → `CustomerServiceVisit.menu_items`; amounts summed in `_visit_recompute_amount_from_menu` + browser script `/api/menu`.
- **Forms:** `CustomerServiceVisitAdmin.scaffold_form` patches `customer` `UnboundField` with `allow_blank=True`. Extra fields: `new_customer_full_name`, `new_customer_phone`.
- **Templates:** `visit_create.html` / `visit_edit.html` + `_visit_form_fields.html` + `_visit_menu_amount_script.html`.

## Token-saving habits

1. **Don’t** re-read all of `sqladmin` site-packages unless debugging upstream; grep `GlamrAdmin`, `CustomerServiceVisitAdmin`, `ajax_lookup`.
2. **Don’t** add README/docs unless asked.
3. **Do** keep changes scoped; match existing patterns in `admin_views.py`.
4. **SQLite:** `create_all` on startup; association tables appear when models change.

## Git

- Repo root may be parent of `sal/`; this project lives under **`sal/`**.
