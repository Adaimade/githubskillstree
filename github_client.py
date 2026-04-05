"""GitHub API calls, skill detection, and aggregation."""
import collections
import os
import logging
import requests

from skills_config import SKILL_MAP, SKILL_LEADS_TO, JOB_MATRIX

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Raw dep file paths tried per repo during deep scan
DEP_FILES = [
    "package.json",
    "requirements.txt",
    "go.mod",
    "Cargo.toml",
    "README.md",
]


def _headers() -> dict:
    h = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def _scan_repo_deps(username: str, repo_name: str) -> list:
    """Grep known skill keywords from dependency files on main branch."""
    found = []
    for fname in DEP_FILES:
        url = f"https://raw.githubusercontent.com/{username}/{repo_name}/main/{fname}"
        try:
            r = requests.get(url, timeout=3)
            if r.status_code != 200:
                continue
            text = r.text.lower()
            for kw, skill in SKILL_MAP.items():
                if kw in text:
                    found.append(skill)
        except requests.RequestException:
            continue
    return found


def _score_skills(repos: list, username: str) -> dict:
    """Weight skills by language, topics, description, stars, and deep scan."""
    scores = collections.defaultdict(int)

    for repo in repos:
        lang = (repo.get("language") or "").lower()
        if lang in SKILL_MAP:
            scores[SKILL_MAP[lang]] += 5

        # Name + description + topics keyword match
        name = repo.get("name", "").lower()
        desc = (repo.get("description") or "").lower()
        topics = " ".join(repo.get("topics") or []).lower()
        haystack = f"{name} {desc} {topics}"
        for kw, skill in SKILL_MAP.items():
            if kw in haystack:
                scores[skill] += 2

        # Star boost for primary language
        stars = repo.get("stargazers_count", 0)
        if stars > 0 and lang in SKILL_MAP:
            scores[SKILL_MAP[lang]] += min(stars, 5)

    # Deep scan top 3 most-recently-pushed repos
    for repo in repos[:3]:
        for skill in _scan_repo_deps(username, repo["name"]):
            scores[skill] += 1

    return scores


def _recommend(top_skill_ids: list) -> list:
    """Suggest up to 5 next skills based on what the user already has."""
    seen = set(top_skill_ids)
    recs = []
    for sid in top_skill_ids:
        for rec in SKILL_LEADS_TO.get(sid, []):
            if rec not in seen:
                recs.append(rec)
                seen.add(rec)
    return recs[:5]


def _match_jobs(top_skill_ids: list) -> list:
    """Return (title, match_pct, salary) sorted by match, top 4."""
    owned = set(top_skill_ids)
    matches = []
    for title, required, salary in JOB_MATRIX:
        overlap = len(owned & set(required))
        pct = int(overlap / len(required) * 100)
        if pct > 0:
            matches.append((title, pct, salary))
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[:4]


def fetch_skill_tree(username: str) -> dict | None:
    """Fetch user + repos, compute skills/recs/jobs. Returns None on failure."""
    try:
        user_resp = requests.get(
            f"{GITHUB_API}/users/{username}", headers=_headers(), timeout=4
        )
        user_resp.raise_for_status()
        user = user_resp.json()

        repos_resp = requests.get(
            f"{GITHUB_API}/users/{username}/repos",
            headers=_headers(),
            params={"per_page": 50, "sort": "pushed"},
            timeout=4,
        )
        repos_resp.raise_for_status()
        repos = repos_resp.json()

        scores = _score_skills(repos, username)
        top_skills = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:8]
        top_ids = [s[0] for s in top_skills]

        lang_counts = collections.Counter(
            r["language"] for r in repos if r.get("language")
        )
        top_langs = lang_counts.most_common(4)

        return {
            "username":    username,
            "avatar_url":  user.get("avatar_url", ""),
            "name":        user.get("name") or username,
            "bio":         (user.get("bio") or "")[:50],
            "repos":       user.get("public_repos", 0),
            "followers":   user.get("followers", 0),
            "top_skills":  top_skills,
            "recommended": _recommend(top_ids),
            "jobs":        _match_jobs(top_ids),
            "top_langs":   top_langs,
            "skill_count": len(top_skills),
        }
    except requests.RequestException as e:
        log.error(f"GitHub fetch failed for {username}: {e}")
        return None
