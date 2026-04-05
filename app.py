"""Flask entry point for the GitHub Skill Tree SVG generator."""
import logging
import os
import threading

from flask import Flask, Response, request

from cache import TTLCache
from github_client import fetch_skill_tree
from svg_render import render_card, render_loading, render_error

app = Flask(__name__)

# Share gunicorn's log handler so messages surface in Zeabur logs
gunicorn_logger = logging.getLogger("gunicorn.error")
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level or logging.INFO)

cache = TTLCache(ttl_seconds=1800)


def _prefetch(username: str) -> None:
    """Populate cache in background so next request is instant."""
    try:
        data = fetch_skill_tree(username)
        if data:
            cache.set(username, data)
    except Exception as e:
        app.logger.error(f"Prefetch failed for {username}: {e}")


def _svg_response(svg: str) -> Response:
    resp = Response(svg.encode("utf-8"), mimetype="image/svg+xml")
    resp.headers["Content-Type"] = "image/svg+xml"
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.route("/")
def index():
    return """<html>
<head><title>GitHub Skill Tree</title></head>
<body style="background:#0f172a;color:#e2e8f0;font-family:monospace;padding:40px">
<h1>GitHub Skill Tree API</h1>
<p>Add to your GitHub Profile README:</p>
<pre style="background:#1e293b;padding:20px;border-radius:8px;color:#10b981">
![Skill Tree](https://github-skillstree.zeabur.app/api/skill-tree?username=YOUR_GITHUB_USERNAME)
</pre>
<p>Preview:</p>
<img src="/api/skill-tree?username=Adaimade" style="border-radius:12px"/>
</body></html>"""


@app.route("/api/skill-tree")
def skill_tree():
    username = request.args.get("username", "").strip()
    if not username:
        return _svg_response(render_error("?username= required"))

    data = cache.get(username)
    if data:
        return _svg_response(render_card(data))

    # Cold cache: return loading SVG immediately, fetch in background
    threading.Thread(target=_prefetch, args=(username,), daemon=True).start()
    return _svg_response(render_loading(username))


@app.route("/api/data")
def api_data():
    username = request.args.get("username", "").strip()
    if not username:
        return {"error": "username required"}, 400
    data = cache.get(username) or fetch_skill_tree(username)
    if not data:
        return {"error": "user not found"}, 404
    cache.set(username, data)
    return data


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, port=port)
