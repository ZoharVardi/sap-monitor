#!/usr/bin/env python3
"""
SAP monitor:

- Calls a list of SAP URLs
- Records latency for each URL as a Prometheus Summary
- Decides if it's safe to deploy (all URLs return a 2xx status code)

(2xx range examples: 200 OK, 201 Created, 204 No Content)

Main thread handles HTTP:

- GET /          -> HTML dashboard (with embedded Grafana)
- GET /metrics   -> Prometheus metrics
- GET /api/gate  -> JSON deployment gate flag (for Jenkins, etc.)

Background thread keeps updating:

- state["can_deploy"]
- state["last_check_ts"]
- Prometheus metrics (endpoint_up, endpoint_latency, monitor_can_deploy)
"""

import threading
import time
from typing import Dict

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, Summary, generate_latest


SAP_URLS = [
    "https://api.sap.com/api/ConcurSharedLists/overview",
    "https://api.sap.com/products/SAPS4HANACloud/apis/packages",
    "https://api.sap.com/odata/1.0/catalog.svc/",
    "https://api.sap.com/content-type/API/apis/all",
]

GRAFANA_URL = (
    "http://localhost:3000/d/adj75mx/sap-monitor"
    "?orgId=1&from=now-3h&to=now&timezone=browser&kiosk"
)

CHECK_INTERVAL_SECONDS = 20

HTTP_TIMEOUT_SECONDS = 3.0


monitor_app = FastAPI()
lock = threading.Lock()

# Shared state used by both the background thread and the HTTP handlers
state: Dict[str, object] = {
    "can_deploy": False,        # True = gate open, False = gate closed
    "last_check_ts": None,      # human readable time string
    "last_overall_ok": None,    # None / True / False
}

#PROMETHEUS METRICS 

# 1 if endpoint is up (2xx), 0 otherwise
endpoint_up = Gauge(
    "endpoint_up",
    "1 if endpoint is up (2xx), else 0",
    ["url"],
)

# Latency per URL
endpoint_latency = Summary(
    "endpoint_latency_seconds",
    "HTTP request latency in seconds",
    ["url"],
)

# Deployment gate flag (no labels, a single global metric)
deploy_gate = Gauge(
    "monitor_can_deploy",
    "Deployment gate flag (1 = can deploy, 0 = do not deploy)",
)


#BACKGROUND HEALTH CHECKING 


def check_once() -> None:
    """
    Run one round of checks against all SAP_URLS.

    For each URL:
      - measure latency
      - consider it healthy only if status code is 2xx

    At the end we update the shared state and the deploy_gate metric.
    """
    all_ok = True

    for url in SAP_URLS:
        start = time.perf_counter()
        ok_flag = 0  # 1 = healthy, 0 = not healthy

        try:
            resp = requests.get(url, timeout=HTTP_TIMEOUT_SECONDS)
            ok_flag = 1 if 200 <= resp.status_code < 300 else 0
        except requests.RequestException as exc:
            # Just log the error; the endpoint is considered "not ok"
            print(f"[monitor-app] Error calling {url}: {exc}")

        duration = time.perf_counter() - start

        # Update Prometheus metrics for this URL
        endpoint_up.labels(url=url).set(ok_flag)
        endpoint_latency.labels(url=url).observe(duration)

        if ok_flag == 0:
            all_ok = False

    # Update shared state + Prometheus gate metric in one critical section
    with lock:
        state["last_overall_ok"] = all_ok
        state["last_check_ts"] = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime()
        )
        state["can_deploy"] = all_ok
        deploy_gate.set(1 if all_ok else 0)


def check_loop() -> None:
    """Background loop that runs forever."""
    while True:
        try:
            # Ping all SAP URLs and measure latency/up status
            check_once()
        except Exception as exc:  # don't ever crash the process
            print(f"[monitor-app] check loop error: {exc}")
        time.sleep(CHECK_INTERVAL_SECONDS)


@monitor_app.on_event("startup")
def on_startup() -> None:
    """
    Start the background checker thread
    and print some useful info to the console.
    """
    t = threading.Thread(target=check_loop, daemon=True)
    t.start()
    print("[monitor-app] background check loop started")
    print("[monitor-app] Using GRAFANA_URL:", GRAFANA_URL)


# HTTP HANDLERS 


@monitor_app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    """Simple HTML control panel with the deployment gate + embedded Grafana."""
    with lock:
        can_deploy = bool(state["can_deploy"])
        last_check_ts = state["last_check_ts"]

    status_label = "OPEN (can deploy)" if can_deploy else "CLOSED (do not deploy)"
    status_class = "ok" if can_deploy else "bad"

    html = f"""
<!doctype html>
<html>
  <head>
    <title>SAP Monitoring Control Panel</title>
    <style>
      body {{
        font-family: system-ui, sans-serif;
        background: #0f172a;
        color: #e5e7eb;
        margin: 20px;
      }}
      h1, h2 {{ margin-top: 0; }}
      .card {{
        border: 1px solid #1f2937;
        background: #020617;
        padding: 16px;
        border-radius: 10px;
        margin-bottom: 16px;
        box-shadow: 0 10px 25px rgba(15,23,42,0.7);
      }}
      .ok  {{ color: #22c55e; font-weight: bold; }}
      .bad {{ color: #ef4444; font-weight: bold; }}
      .meta {{ font-size: 0.85rem; color: #9ca3af; }}
      iframe {{
        border-radius: 8px;
        border: 1px solid #1f2937;
      }}
      a {{ color: #38bdf8; }}
    </style>
  </head>
  <body>
    <h1>SAP Monitoring Control Panel (FastAPI)</h1>

    <div class="card">
      <h2>Deployment Gate</h2>
      <p>Status:
        <span class="{status_class}">{status_label}</span>
      </p>
      <p class="meta">Last check: {last_check_ts or 'n/a'}</p>
    </div>

    <div class="card">
      <h2>Grafana Dashboard</h2>
      <p class="meta">
        Embedded Grafana dashboard below. If it doesn't render, you can
        <a href="{GRAFANA_URL}" target="_blank">open it in a new tab</a>.
      </p>
      <iframe
        src="{GRAFANA_URL}"
        width="100%"
        height="420"
        style="border:none; min-height:420px;"
      ></iframe>
    </div>
  </body>
</html>
"""
    return HTMLResponse(content=html)


@monitor_app.get("/metrics")
def metrics() -> PlainTextResponse:
    """
    /metrics endpoint – exposed for Prometheus scraping.
    """
    data = generate_latest()
    return PlainTextResponse(content=data, media_type=CONTENT_TYPE_LATEST)


@monitor_app.get("/api/gate")
def api_gate() -> JSONResponse:
    """
    Simple JSON endpoint for Jenkins / other tools
    that just says whether deployment is allowed.
    """
    with lock:
        gate = bool(state["can_deploy"])
    return JSONResponse({"can_deploy": gate})
