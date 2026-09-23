"""
SWE40006 Task 4.2: basic Flask app for the containerisation task.

Listens on PORT (default 5000) and binds to 0.0.0.0 so it can be reached
through the port published with `docker run -p`.
"""
import os
import platform
import socket
from datetime import datetime, timezone

from flask import Flask, jsonify

app = Flask(__name__)

PORT = int(os.environ.get("PORT", "5000"))
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
STARTED_AT = datetime.now(timezone.utc)


def container_info():
    return {
        "app": "swe40006-flask-app",
        "version": APP_VERSION,
        "hostname": socket.gethostname(),  # this is the container ID inside Docker
        "python": platform.python_version(),
        "port": PORT,
        "started_at": STARTED_AT.isoformat(timespec="seconds"),
        "server_time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@app.get("/")
def index():
    info = container_info()
    rows = "".join(
        f"<tr><th>{key}</th><td>{value}</td></tr>" for key, value in info.items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SWE40006 Task 4.2</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; max-width: 640px; margin: 40px auto; color: #222; }}
    h1 {{ color: #0db7ed; margin-bottom: 4px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f4f8fb; width: 35%; }}
  </style>
</head>
<body>
  <h1>Hello from a Docker container!</h1>
  <p>SWE40006 Deployment Task 4.2 | Aryan Thakor (105061154)</p>
  <table>{rows}</table>
</body>
</html>"""


@app.get("/api/info")
def api_info():
    return jsonify(container_info())


@app.get("/health")
def health():
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    # needs 0.0.0.0, with 127.0.0.1 the port mapping can't reach the app
    app.run(host="0.0.0.0", port=PORT)
