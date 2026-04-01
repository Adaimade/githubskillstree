from flask import Flask, Response, render_template, request
import requests
import os
import json
import collections
import math
import logging
import time
import threading
from pathlib import Path

app = Flask(__name__)

# In-memory cache: username -> (timestamp, data)
_CACHE = {}
_CACHE_TTL = 1800  # 30 min

gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_API = "https://api.github.com"

# ─────────────────────────────────────────
# 技能本體：語言 / 框架 / 工具 → 技能ID
# ─────────────────────────────────────────
SKILL_MAP = {
    # 語言
    "python": "python", "javascript": "javascript", "typescript": "typescript",
    "java": "java", "go": "go", "rust": "rust", "c++": "cpp", "c": "c",
    "c#": "csharp", "ruby": "ruby", "php": "php", "swift": "swift",
    "kotlin": "kotlin", "scala": "scala", "shell": "bash", "dockerfile": "docker",
    "html": "html", "css": "css", "r": "r", "lua": "lua", "dart": "dart",
    # 框架 / 工具（README / package.json 關鍵字）
    "react": "react", "vue": "vue", "angular": "angular", "next": "nextjs",
    "nuxt": "nuxt", "django": "django", "flask": "flask", "fastapi": "fastapi",
    "express": "express", "spring": "spring", "rails": "rails", "laravel": "laravel",
    "docker": "docker", "kubernetes": "kubernetes", "k8s": "kubernetes",
    "aws": "aws", "gcp": "gcp", "azure": "azure", "terraform": "terraform",
    "ansible": "ansible", "postgres": "postgresql", "postgresql": "postgresql",
    "mysql": "mysql", "mongodb": "mongodb", "redis": "redis",
    "graphql": "graphql", "pytorch": "pytorch", "tensorflow": "tensorflow",
    "pandas": "pandas", "numpy": "numpy", "scikit": "sklearn",
}

# 技能 → 推薦衍生技能
SKILL_LEADS_TO = {
    "python":     ["fastapi", "django", "pytorch", "sklearn"],
    "javascript": ["typescript", "react", "nodejs", "nextjs"],
    "typescript": ["react", "nextjs", "nodejs"],
    "react":      ["nextjs", "typescript", "graphql"],
    "java":       ["spring", "kubernetes", "scala"],
    "go":         ["kubernetes", "docker", "grpc"],
    "docker":     ["kubernetes", "terraform", "aws"],
    "kubernetes": ["terraform", "aws", "sre"],
    "django":     ["postgresql", "redis", "fastapi"],
    "fastapi":    ["postgresql", "redis", "docker"],
    "pytorch":    ["tensorflow", "sklearn", "mlops"],
    "aws":        ["terraform", "kubernetes", "serverless"],
}

# 職位對應技能組合
JOB_MATRIX = [
    ("Backend Engineer",      ["python", "django", "postgresql", "docker"],        "$105K–$145K"),
    ("Frontend Engineer",     ["javascript", "react", "typescript", "css"],        "$95K–$130K"),
    ("Full Stack Engineer",   ["javascript", "react", "nodejs", "postgresql"],     "$110K–$148K"),
    ("DevOps / SRE",          ["docker", "kubernetes", "terraform", "linux"],      "$120K–$160K"),
    ("Data Scientist",        ["python", "pandas", "sklearn", "pytorch"],          "$110K–$155K"),
    ("ML Engineer",           ["python", "pytorch", "tensorflow", "docker"],       "$125K–$170K"),
    ("Cloud Architect",       ["aws", "terraform", "kubernetes", "docker"],        "$140K–$185K"),
    ("Mobile Engineer",       ["swift", "kotlin", "react"],                        "$105K–$145K"),
    ("Platform Engineer",     ["kubernetes", "go", "docker", "terraform"],         "$135K–$175K"),
]

# 語言顏色
LANG_COLOR = {
    "python": "#3572A5", "javascript": "#f1e05a", "typescript": "#3178c6",
    "java": "#b07219", "go": "#00ADD8", "rust": "#dea584", "cpp": "#f34b7d",
    "c": "#555555", "csharp": "#178600", "ruby": "#701516", "php": "#4F5D95",
    "swift": "#FA7343", "kotlin": "#7F52FF", "html": "#e34c26", "css": "#563d7c",
    "shell": "#89e051", "bash": "#89e051", "docker": "#2496ED",
}

# ─────────────────────────────────────────
# GitHub 資料抓取
# ─────────────────────────────────────────
def gh_headers():
    h = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h

def detect_skills_from_repo_detail(username: str, repo_name: str, headers: dict) -> list:
    """嘗試從 package.json / requirements.txt / go.mod 抓取依賴"""
    skills = []
    dep_files = [
        f"https://raw.githubusercontent.com/{username}/{repo_name}/main/package.json",
        f"https://raw.githubusercontent.com/{username}/{repo_name}/main/requirements.txt",
        f"https://raw.githubusercontent.com/{username}/{repo_name}/main/go.mod",
        f"https://raw.githubusercontent.com/{username}/{repo_name}/main/Cargo.toml",
        f"https://raw.githubusercontent.com/{username}/{repo_name}/main/README.md",
    ]
    for url in dep_files:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                text = r.text.lower()
                for kw, skill in SKILL_MAP.items():
                    if kw in text:
                        skills.append(skill)
        except Exception:
            pass
    return skills

def detect_skills_from_repos(repos, username="", headers=None):
    skill_counts = collections.defaultdict(int)
    for repo in repos:
        # 語言（加重）
        lang = (repo.get("language") or "").lower()
        if lang and lang in SKILL_MAP:
            skill_counts[SKILL_MAP[lang]] += 5

        # 倉庫名稱 + 描述
        name = repo.get("name", "").lower()
        desc = (repo.get("description") or "").lower()
        topics = " ".join(repo.get("topics") or []).lower()
        text = f"{name} {desc} {topics}"
        for kw, skill in SKILL_MAP.items():
            if kw in text:
                skill_counts[skill] += 2

        # 從 Star 數判斷重要性加成
        stars = repo.get("stargazers_count", 0)
        if stars > 0 and lang and lang in SKILL_MAP:
            skill_counts[SKILL_MAP[lang]] += min(stars, 5)

    # 從前 3 個倉庫深度掃描依賴文件
    if username and headers:
        for repo in repos[:3]:
            extra = detect_skills_from_repo_detail(username, repo["name"], headers)
            for s in extra:
                skill_counts[s] += 1

    return skill_counts

def get_skill_tree_data(username: str):
    # Return cached result if fresh
    cached = _CACHE.get(username)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        return cached[1]

    headers = gh_headers()
    try:
        # 用戶基本資料
        ur = requests.get(f"{GITHUB_API}/users/{username}", headers=headers, timeout=4)
        ur.raise_for_status()
        ud = ur.json()

        # 取得倉庫
        rr = requests.get(
            f"{GITHUB_API}/users/{username}/repos",
            headers=headers, params={"per_page": 50, "sort": "pushed"}, timeout=4
        )
        rr.raise_for_status()
        repos = rr.json()

        # 技能偵測（含深度掃描）
        skill_counts = detect_skills_from_repos(repos, username=username, headers=headers)

        # 排序後取前 8 技能
        top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        top_skill_ids = [s[0] for s in top_skills]

        # 推薦技能（不重複）
        recommended = []
        for sid in top_skill_ids:
            for rec in SKILL_LEADS_TO.get(sid, []):
                if rec not in top_skill_ids and rec not in recommended:
                    recommended.append(rec)
        recommended = recommended[:5]

        # 職位匹配
        matched_jobs = []
        skill_set = set(top_skill_ids)
        for title, reqs, salary in JOB_MATRIX:
            matched = len(skill_set & set(reqs))
            pct = int(matched / len(reqs) * 100)
            if pct > 0:
                matched_jobs.append((title, pct, salary))
        matched_jobs.sort(key=lambda x: x[1], reverse=True)

        # 語言統計（顯示用）
        lang_counts = collections.defaultdict(int)
        for repo in repos:
            if lang := repo.get("language"):
                lang_counts[lang] += 1
        top_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:4]

        result = {
            "username":    username,
            "avatar_url":  ud.get("avatar_url", ""),
            "name":        ud.get("name") or username,
            "bio":         (ud.get("bio") or "")[:50],
            "repos":       ud.get("public_repos", 0),
            "followers":   ud.get("followers", 0),
            "top_skills":  top_skills,
            "recommended": recommended,
            "jobs":        matched_jobs[:4],
            "top_langs":   top_langs,
            "skill_count": len(top_skills),
        }
        _CACHE[username] = (time.time(), result)
        return result
    except Exception as e:
        app.logger.error(f"Error: {e}")
        # Return stale cache on error rather than None
        if cached:
            return cached[1]
        return None

# ─────────────────────────────────────────
# 星空粒子 + 技能節點圖生成
# ─────────────────────────────────────────
import random, hashlib

def _stars(seed: str, count: int, W: int, H: int) -> str:
    rng = random.Random(seed)
    out = ""
    for _ in range(count):
        x = rng.randint(2, W - 2)
        y = rng.randint(2, H - 2)
        r = rng.choice([0.6, 0.8, 1.0, 1.2])
        op = rng.uniform(0.3, 0.9)
        out += f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" opacity="{op:.2f}"/>'
    return out

def _node(x, y, label, color, r=34, icon=None, alpha=1.0):
    """圓形節點：外環發光 + 圖示 + 標籤"""
    label_short = label[:10].upper()
    op = f'opacity="{alpha}"'
    return f"""
    <g {op}>
      <!-- 外環光暈 -->
      <circle cx="{x}" cy="{y}" r="{r+8}" fill="none"
              stroke="{color}" stroke-width="1.2" opacity="0.25" filter="url(#glow)"/>
      <!-- 主圓 -->
      <circle cx="{x}" cy="{y}" r="{r}" fill="#0a0f1e"
              stroke="{color}" stroke-width="2" filter="url(#glow)"/>
      <!-- 內圓紋 -->
      <circle cx="{x}" cy="{y}" r="{r-8}" fill="none"
              stroke="{color}" stroke-width="0.6" opacity="0.4"/>
      <!-- 標籤 -->
      <text x="{x}" y="{y+r+14}" fill="{color}" font-size="10"
            font-family="'Courier New',monospace" text-anchor="middle"
            filter="url(#glow)">{label_short}</text>
    </g>"""

def _line(x1, y1, x2, y2, color, dash=False):
    """發光連線"""
    da = 'stroke-dasharray="5,4"' if dash else ""
    return f"""
    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"
          stroke="{color}" stroke-width="1.2" opacity="0.5"
          filter="url(#glow)" {da}/>
    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"
          stroke="{color}" stroke-width="0.4" opacity="0.8" {da}/>"""

def _particle_dots(x1, y1, x2, y2, color, seed):
    """沿連線散佈粒子"""
    rng = random.Random(seed)
    out = ""
    for i in range(4):
        t = rng.uniform(0.2, 0.8)
        px = x1 + (x2 - x1) * t + rng.uniform(-4, 4)
        py = y1 + (y2 - y1) * t + rng.uniform(-4, 4)
        r  = rng.uniform(1.2, 2.5)
        out += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" fill="{color}" opacity="0.7" filter="url(#glow)"/>'
    return out

def render_skill_tree_svg(data: dict) -> str:
    if not data:
        return _error_svg("User not found")

    W, H = 500, 640
    skills  = data["top_skills"][:7]
    recs    = data["recommended"][:5]
    uname   = data["username"]
    repos   = data["repos"]
    followers = data["followers"]

    # ── 色盤
    PALETTE = ["#00ffcc", "#00ccff", "#7c3aed", "#f59e0b",
               "#10b981", "#3b82f6", "#ec4899", "#f97316"]

    # ── 中心座標
    CX, CY = W // 2, 300

    # ── 技能節點座標（第一環：已掌握）
    n1 = len(skills)
    layer1 = []
    for i, (sid, cnt) in enumerate(skills):
        angle = math.radians(360 / n1 * i - 90)
        R1 = 145
        x = CX + R1 * math.cos(angle)
        y = CY + R1 * math.sin(angle)
        layer1.append((x, y, sid, cnt))

    # ── 推薦節點（第二環）
    n2 = len(recs)
    layer2 = []
    for i, sid in enumerate(recs):
        angle = math.radians(360 / max(n2, 1) * i - 60)
        R2 = 250
        x = CX + R2 * math.cos(angle)
        y = CY + R2 * math.sin(angle)
        layer2.append((x, y, sid))

    # ── SVG 組裝
    stars_svg    = _stars(uname, 120, W, H)
    lines_svg    = ""
    particles_svg = ""
    nodes_svg    = ""

    # 連線：中心 → 第一環
    for i, (x, y, sid, cnt) in enumerate(layer1):
        col = LANG_COLOR.get(sid, PALETTE[i % len(PALETTE)])
        lines_svg     += _line(CX, CY, x, y, col)
        particles_svg += _particle_dots(CX, CY, x, y, col, f"{uname}{sid}")

    # 連線：第一環 → 第二環（對應最近的技能）
    for j, (x2, y2, sid2) in enumerate(layer2):
        src_i = j % max(len(layer1), 1)
        x1, y1, s1, _ = layer1[src_i]
        col = "#39ff14"
        lines_svg     += _line(x1, y1, x2, y2, col, dash=True)
        particles_svg += _particle_dots(x1, y1, x2, y2, col, f"rec{sid2}")

    # 第一環節點
    for i, (x, y, sid, cnt) in enumerate(layer1):
        col = LANG_COLOR.get(sid, PALETTE[i % len(PALETTE)])
        nodes_svg += _node(int(x), int(y), sid, col, r=30)

    # 第二環節點（推薦，虛線感、稍透明）
    for j, (x, y, sid) in enumerate(layer2):
        nodes_svg += _node(int(x), int(y), sid, "#39ff14", r=22, alpha=0.85)

    # 中心節點（用戶）
    center_node = f"""
    <g>
      <circle cx="{CX}" cy="{CY}" r="52" fill="#0a0f1e"
              stroke="#00ffcc" stroke-width="2.5" filter="url(#glow)"/>
      <circle cx="{CX}" cy="{CY}" r="44" fill="none"
              stroke="#00ffcc" stroke-width="0.8" opacity="0.4"/>
      <circle cx="{CX}" cy="{CY}" r="36" fill="none"
              stroke="#00ffcc" stroke-width="0.4" opacity="0.2"/>
      <text x="{CX}" y="{CY - 8}" fill="#00ffcc" font-size="12"
            font-family="'Courier New',monospace" text-anchor="middle"
            font-weight="bold" filter="url(#glow)">@{uname[:12]}</text>
      <text x="{CX}" y="{CY + 8}" fill="#00ccff" font-size="9"
            font-family="'Courier New',monospace" text-anchor="middle">
        {repos} repos</text>
      <text x="{CX}" y="{CY + 20}" fill="#00ccff" font-size="9"
            font-family="'Courier New',monospace" text-anchor="middle">
        {followers} followers</text>
    </g>"""

    # 標題 + 底部說明
    title_svg = f"""
    <text x="{W//2}" y="36" fill="#00ffcc" font-size="18"
          font-family="'Courier New',monospace" text-anchor="middle"
          font-weight="bold" letter-spacing="4" filter="url(#glow)">GITHUB SKILL TREE</text>
    <text x="{W//2}" y="56" fill="#64748b" font-size="10"
          font-family="'Courier New',monospace" text-anchor="middle">
      ● CURRENT SKILLS  ─ ─  RECOMMENDED NEXT</text>"""

    legend_svg = f"""
    <circle cx="30" cy="{H-20}" r="5" fill="#00ffcc" filter="url(#glow)"/>
    <text x="40" y="{H-15}" fill="#475569" font-size="9" font-family="monospace">Current Skills</text>
    <circle cx="130" cy="{H-20}" r="5" fill="#39ff14" opacity="0.85" filter="url(#glow)"/>
    <text x="140" y="{H-15}" fill="#475569" font-size="9" font-family="monospace">Recommended</text>
    <text x="{W-10}" y="{H-15}" fill="#1e293b" font-size="8" font-family="monospace"
          text-anchor="end">github-skillstree.zeabur.app</text>"""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <radialGradient id="bg" cx="50%" cy="50%" r="70%">
      <stop offset="0%"   stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#020409"/>
    </radialGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <filter id="glow2" x="-80%" y="-80%" width="260%" height="260%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <rect width="{W}" height="{H}" rx="14" fill="url(#bg)"/>
  {stars_svg}
  <rect width="{W}" height="{H}" rx="14" fill="none"
        stroke="#00ffcc" stroke-width="1" opacity="0.3" filter="url(#glow)"/>
  {lines_svg}
  {particles_svg}
  {title_svg}
  {center_node}
  {nodes_svg}
  {legend_svg}
</svg>"""

    return svg

def _error_svg(msg: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="500" height="100">
  <rect width="500" height="100" rx="12" fill="#020409" stroke="#ef4444" stroke-width="1"/>
  <text x="250" y="55" fill="#ef4444" font-size="14" font-family="monospace"
        text-anchor="middle">{msg}</text>
</svg>"""

def _loading_svg(username: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="500" height="640" viewBox="0 0 500 640">
  <defs>
    <radialGradient id="bg" cx="50%" cy="50%" r="70%">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#020409"/>
    </radialGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect width="500" height="640" rx="14" fill="url(#bg)"/>
  <rect width="500" height="640" rx="14" fill="none" stroke="#00ffcc" stroke-width="1" opacity="0.3"/>
  <text x="250" y="290" fill="#00ffcc" font-size="18" font-family="'Courier New',monospace"
        text-anchor="middle" font-weight="bold" letter-spacing="4" filter="url(#glow)">GITHUB SKILL TREE</text>
  <text x="250" y="330" fill="#00ccff" font-size="13" font-family="'Courier New',monospace"
        text-anchor="middle" filter="url(#glow)">@{username[:20]}</text>
  <text x="250" y="365" fill="#475569" font-size="11" font-family="'Courier New',monospace"
        text-anchor="middle">Analyzing repositories...</text>
  <text x="250" y="395" fill="#1e3a2f" font-size="10" font-family="monospace"
        text-anchor="middle">Refresh in a few seconds</text>
</svg>"""

# ─────────────────────────────────────────
# Flask Routes
# ─────────────────────────────────────────
@app.route("/")
def index():
    return """
    <html><head><title>GitHub Skill Tree</title></head>
    <body style="background:#0f172a;color:#e2e8f0;font-family:monospace;padding:40px">
    <h1>🌳 GitHub Skill Tree API</h1>
    <p>在你的 GitHub Profile README 中加入：</p>
    <pre style="background:#1e293b;padding:20px;border-radius:8px;color:#10b981">
![Skill Tree](https://github-skillstree.zeabur.app/api/skill-tree?username=YOUR_GITHUB_USERNAME)
    </pre>
    <p>預覽範例：</p>
    <img src="/api/skill-tree?username=Adaimade" style="border-radius:12px"/>
    </body></html>
    """

def _fetch_bg(username):
    """Fetch data in background and store to cache."""
    try:
        get_skill_tree_data(username)
    except Exception:
        pass

@app.route("/api/skill-tree")
def skill_tree():
    username = request.args.get("username", "").strip()
    if not username:
        return Response(_error_svg("?username= required"), mimetype="image/svg+xml")

    cached = _CACHE.get(username)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        # Cache hit — respond instantly
        svg = render_skill_tree_svg(cached[1])
    else:
        # No cache — return loading SVG immediately, fetch in background
        threading.Thread(target=_fetch_bg, args=(username,), daemon=True).start()
        svg = _loading_svg(username)

    resp = Response(svg.encode("utf-8"), mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Content-Type"] = "image/svg+xml"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp

@app.route("/api/data")
def api_data():
    """返回 JSON 資料（給前端或測試用）"""
    username = request.args.get("username", "").strip()
    if not username:
        return {"error": "username required"}, 400
    data = get_skill_tree_data(username)
    if not data:
        return {"error": "user not found"}, 404
    return data

if __name__ == "__main__":
    app.run(debug=False, port=5000)
