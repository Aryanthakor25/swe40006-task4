"""StudyPulse: small study-session tracker for SWE40006 Task 4.3.

Log study time per unit and see the totals. All config comes from env vars.
"""
import logging
import socket
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from .config import load_settings
from .store import build_store

settings = load_settings()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("studypulse")

app = FastAPI(title=settings.app_title, version=settings.app_version)
store = build_store(settings)
STARTED_AT = datetime.now(timezone.utc)


class SessionIn(BaseModel):
    unit_code: str = Field(pattern=r"^[A-Za-z]{3}\d{5}$", examples=["SWE40006"])
    minutes: int = Field(ge=1, le=600)
    note: str = Field(default="", max_length=200)


@app.get("/health")
def health():
    ok = store.ping()
    body = {"status": "ok" if ok else "degraded", "backend": store.backend}
    return JSONResponse(body, status_code=200 if ok else 503)


@app.get("/api/info")
def info():
    return {
        "app": settings.app_title,
        "environment": settings.app_env,
        "version": settings.app_version,
        "container_hostname": socket.gethostname(),
        "storage_backend": store.backend,
        "started_at": STARTED_AT.isoformat(timespec="seconds"),
    }


@app.get("/api/sessions")
def list_sessions(limit: int = 50):
    try:
        return store.list_sessions(limit=max(1, min(limit, 200)))
    except Exception as exc:
        log.error("Could not read sessions: %s", exc)
        raise HTTPException(status_code=503, detail="storage unavailable")


@app.post("/api/sessions", status_code=201)
def add_session(payload: SessionIn):
    session = {
        "unit_code": payload.unit_code.upper(),
        "minutes": payload.minutes,
        "note": payload.note.strip(),
        "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    try:
        store.add_session(session)
    except Exception as exc:
        log.error("Could not save session: %s", exc)
        raise HTTPException(status_code=503, detail="storage unavailable")
    log.info("Logged %s min for %s", session["minutes"], session["unit_code"])
    return session


@app.get("/api/stats")
def stats():
    totals: dict[str, int] = defaultdict(int)
    sessions = store.list_sessions(limit=1000)
    for s in sessions:
        totals[s["unit_code"]] += s["minutes"]
    return {
        "total_sessions": len(sessions),
        "total_minutes": sum(totals.values()),
        "minutes_per_unit": dict(sorted(totals.items(), key=lambda kv: -kv[1])),
    }


@app.get("/", response_class=HTMLResponse)
def index():
    try:
        visits = store.incr_visits()
    except Exception:
        visits = "n/a"
    host = socket.gethostname()
    env_badge = "#2e7d32" if settings.app_env == "production" else "#ef6c00"
    return PAGE.format(
        title=settings.app_title,
        env=settings.app_env,
        env_colour=env_badge,
        version=settings.app_version,
        host=host,
        backend=store.backend,
        visits=visits,
    )


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --blue:#1d63ed; --ink:#1b1f24; --muted:#5b6470; --line:#e3e7ec; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:"Segoe UI",Roboto,Arial,sans-serif; color:var(--ink); background:#f6f8fa; }}
  header {{ background:var(--blue); color:#fff; padding:20px 16px; }}
  header h1 {{ margin:0; font-size:26px; }}
  header p {{ margin:4px 0 0; opacity:.9; }}
  main {{ max-width:900px; margin:0 auto; padding:16px; display:grid; gap:16px; }}
  .card {{ background:#fff; border:1px solid var(--line); border-radius:10px; padding:16px; }}
  .meta {{ display:flex; flex-wrap:wrap; gap:8px; font-size:13px; }}
  .pill {{ background:#eef2f7; border-radius:999px; padding:4px 10px; }}
  .env {{ background:{env_colour}; color:#fff; }}
  form {{ display:grid; grid-template-columns:1fr 110px 2fr auto; gap:8px; }}
  input, button {{ font:inherit; padding:8px 10px; border:1px solid var(--line); border-radius:6px; }}
  button {{ background:var(--blue); color:#fff; border:none; cursor:pointer; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  th, td {{ text-align:left; padding:8px; border-bottom:1px solid var(--line); }}
  .bar {{ height:10px; background:var(--blue); border-radius:4px; }}
  #msg {{ color:#c62828; font-size:13px; min-height:18px; }}
  @media (max-width:640px) {{ form {{ grid-template-columns:1fr 1fr; }} }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <p>Track study time per unit | SWE40006 Deployment Task 4.3</p>
</header>
<main>
  <section class="card meta">
    <span class="pill env">env: {env}</span>
    <span class="pill">version: {version}</span>
    <span class="pill">container: {host}</span>
    <span class="pill">storage: {backend}</span>
    <span class="pill">page visits: {visits}</span>
  </section>

  <section class="card">
    <h2 style="margin-top:0">Log a study session</h2>
    <form id="f">
      <input name="unit_code" placeholder="Unit code e.g. SWE40006" required>
      <input name="minutes" type="number" min="1" max="600" placeholder="Minutes" required>
      <input name="note" maxlength="200" placeholder="What did you work on?">
      <button type="submit">Add</button>
    </form>
    <div id="msg"></div>
  </section>

  <section class="card">
    <h2 style="margin-top:0">Minutes per unit</h2>
    <table id="stats"><tbody></tbody></table>
  </section>

  <section class="card">
    <h2 style="margin-top:0">Recent sessions</h2>
    <table><thead><tr><th>Unit</th><th>Minutes</th><th>Note</th><th>Logged (UTC)</th></tr></thead>
    <tbody id="sessions"></tbody></table>
  </section>
</main>
<script>
function cell(tr, text) {{ const td = document.createElement('td'); td.textContent = text; tr.appendChild(td); return td; }}

async function refresh() {{
  const [sessions, stats] = await Promise.all([
    fetch('/api/sessions').then(r => r.json()),
    fetch('/api/stats').then(r => r.json())
  ]);
  const tb = document.getElementById('sessions'); tb.innerHTML = '';
  sessions.forEach(s => {{
    const tr = document.createElement('tr');
    cell(tr, s.unit_code); cell(tr, s.minutes); cell(tr, s.note); cell(tr, s.logged_at.replace('T',' ').replace('+00:00',''));
    tb.appendChild(tr);
  }});
  const st = document.querySelector('#stats tbody'); st.innerHTML = '';
  const max = Math.max(1, ...Object.values(stats.minutes_per_unit));
  Object.entries(stats.minutes_per_unit).forEach(([unit, mins]) => {{
    const tr = document.createElement('tr');
    cell(tr, unit).style.width = '120px';
    cell(tr, mins + ' min').style.width = '90px';
    const bar = document.createElement('div'); bar.className = 'bar'; bar.style.width = (mins / max * 100) + '%';
    cell(tr, '').appendChild(bar);
    st.appendChild(tr);
  }});
}}

document.getElementById('f').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {{ unit_code: fd.get('unit_code'), minutes: Number(fd.get('minutes')), note: fd.get('note') || '' }};
  const res = await fetch('/api/sessions', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify(body) }});
  document.getElementById('msg').textContent = res.ok ? '' : 'Could not save. Check the unit code (e.g. SWE40006) and minutes (1 to 600).';
  if (res.ok) {{ e.target.reset(); refresh(); }}
}});
refresh();
</script>
</body>
</html>"""
