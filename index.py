"""Vercel Serverless Entrypoint for QEVN Lead Intelligence Platform.

Provides REST API endpoints and platform health dashboard.
Interactive Streamlit application runs via `streamlit run app/Home.py`.
"""

import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
for p in (str(SRC_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


def get_html_dashboard() -> str:
    """Generate dark glassmorphic status dashboard for Vercel landing."""
    total_leads = 0
    hot_count = 0
    try:
        from linkedin_intelligence.db.repository import get_lead_repository

        repo = get_lead_repository()
        stats = repo.get_stats()
        total_leads = stats.get("total_leads", 0)
        hot_count = stats.get("hot_count", 0)
    except Exception:
        pass

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QEVN Lead Intelligence Platform & API</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #07090e;
            --card-bg: rgba(18, 24, 38, 0.7);
            --border: rgba(255, 255, 255, 0.08);
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.15);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }}
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            background-color: var(--bg);
            background-image:
                radial-gradient(at 15% 15%, rgba(56, 189, 248, 0.12) 0px, transparent 50%),
                radial-gradient(at 85% 85%, rgba(129, 140, 248, 0.12) 0px, transparent 50%);
            color: var(--text-main);
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}
        .container {{
            max-width: 860px;
            width: 100%;
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }}
        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            margin-bottom: 16px;
        }}
        .badge::before {{
            content: '';
            display: inline-block;
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #34d399;
            margin-right: 8px;
            box-shadow: 0 0 8px #34d399;
        }}
        h1 {{
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 12px;
        }}
        p.desc {{
            color: var(--text-muted);
            font-size: 1.05rem;
            line-height: 1.6;
            margin-bottom: 32px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .kpi {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}
        .kpi-num {{
            font-size: 2rem;
            font-weight: 800;
            color: #ffffff;
        }}
        .kpi-label {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-top: 4px;
        }}
        .section-title {{
            font-size: 1rem;
            font-weight: 700;
            color: #e2e8f0;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .endpoints {{
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 28px;
        }}
        .endpoint-row {{
            display: flex;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.04);
            font-size: 0.9rem;
        }}
        .endpoint-row:last-child {{ border-bottom: none; }}
        .method {{
            font-size: 0.75rem;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 4px;
            margin-right: 12px;
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            font-family: monospace;
        }}
        .path {{
            font-family: monospace;
            color: #f1f5f9;
            text-decoration: none;
            flex-grow: 1;
        }}
        .path:hover {{ text-decoration: underline; color: #38bdf8; }}
        .note {{
            font-size: 0.85rem;
            color: #64748b;
        }}
        .footer {{
            border-top: 1px solid var(--border);
            padding-top: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            color: var(--text-muted);
        }}
        .footer a {{
            color: #818cf8;
            text-decoration: none;
            font-weight: 600;
        }}
        .footer a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="badge">SYSTEM OPERATIONAL</div>
        <h1>QEVN Lead Intelligence</h1>
        <p class="desc">
            Multi-Agent LinkedIn B2B Prospecting & Intelligence Engine powered by LangGraph, Apify MCP, and Supervised ML Qualification.
        </p>

        <div class="grid">
            <div class="kpi">
                <div class="kpi-num">{total_leads}</div>
                <div class="kpi-label">Repository Leads</div>
            </div>
            <div class="kpi">
                <div class="kpi-num" style="color:#f87171;">{hot_count}</div>
                <div class="kpi-label">HOT Opportunities</div>
            </div>
            <div class="kpi">
                <div class="kpi-num" style="color:#34d399;">18-Dim</div>
                <div class="kpi-label">Feature Scoring</div>
            </div>
        </div>

        <div class="section-title">Available REST API Endpoints</div>
        <div class="endpoints">
            <div class="endpoint-row">
                <span class="method">GET</span>
                <a class="path" href="/api/health">/api/health</a>
                <span class="note">Runtime diagnostics & health status</span>
            </div>
            <div class="endpoint-row">
                <span class="method">GET</span>
                <a class="path" href="/api/stats">/api/stats</a>
                <span class="note">Pipeline KPI aggregates & distribution</span>
            </div>
            <div class="endpoint-row">
                <span class="method">GET</span>
                <a class="path" href="/api/leads">/api/leads</a>
                <span class="note">Master lead records with strategic analysis</span>
            </div>
        </div>

        <div class="footer">
            <span>To launch the full interactive Streamlit interface run: <code>streamlit run app/Home.py</code></span>
            <a href="https://github.com/qevn-org/Qevn-ALG" target="_blank">GitHub Repository &rarr;</a>
        </div>
    </div>
</body>
</html>"""


def app(environ, start_response):
    """WSGI application entrypoint compliant with Vercel Python runtime."""
    path = environ.get("PATH_INFO", "/") or "/"
    method = environ.get("REQUEST_METHOD", "GET").upper()

    headers = [
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
        ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
    ]

    if method == "OPTIONS":
        start_response("204 No Content", headers)
        return [b""]

    # Health API
    if path == "/api/health":
        body = json.dumps(
            {
                "status": "healthy",
                "service": "QEVN Lead Intelligence Platform",
                "version": "0.1.0",
                "environment": "vercel-serverless",
            }
        ).encode("utf-8")
        headers.append(("Content-Type", "application/json"))
        start_response("200 OK", headers)
        return [body]

    # Stats API
    if path == "/api/stats":
        try:
            from linkedin_intelligence.db.repository import get_lead_repository

            repo = get_lead_repository()
            stats = repo.get_stats()
        except Exception as e:
            stats = {"error": str(e)}

        body = json.dumps(stats).encode("utf-8")
        headers.append(("Content-Type", "application/json"))
        start_response("200 OK", headers)
        return [body]

    # Leads API
    if path == "/api/leads":
        try:
            from linkedin_intelligence.db.repository import get_lead_repository

            repo = get_lead_repository()
            query_string = environ.get("QUERY_STRING", "")
            params = parse_qs(query_string)
            limit = int(params.get("limit", [50])[0])
            temperature = params.get("temperature", [None])[0]

            leads = repo.list_leads(temperature=temperature, limit=limit)
            leads_data = [lead_item.model_dump(mode="json") for lead_item in leads]
            res = {"count": len(leads_data), "leads": leads_data}
        except Exception as e:
            res = {"error": str(e), "count": 0, "leads": []}

        body = json.dumps(res).encode("utf-8")
        headers.append(("Content-Type", "application/json"))
        start_response("200 OK", headers)
        return [body]

    # Root / HTML dashboard
    body = get_html_dashboard().encode("utf-8")
    headers.append(("Content-Type", "text/html; charset=utf-8"))
    start_response("200 OK", headers)
    return [body]


# Also support standard callable name for frameworks
application = app

if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    print("Serving on http://localhost:8000...")
    httpd = make_server("0.0.0.0", 8000, app)
    httpd.serve_forever()
