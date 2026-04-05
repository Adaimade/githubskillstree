"""SVG rendering for the skill tree card."""
import math
import random

from skills_config import LANG_COLOR, PALETTE

# Canvas (landscape)
W, H = 800, 400
CX, CY = W // 2, 215

# Layout — ellipse rings stretch horizontally to fill landscape canvas
RX_INNER, RY_INNER = 175, 100   # current skills ring
RX_OUTER, RY_OUTER = 290, 135   # recommended ring
R_CENTER = 48   # user center node
R_SKILL = 27    # current skill node
R_REC = 21      # recommended node

REC_COLOR = "#39ff14"
ACCENT = "#00ffcc"
SECONDARY = "#00ccff"


# ── Primitives ────────────────────────────────────────────
def _stars(seed: str, count: int = 120) -> str:
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        x = rng.randint(2, W - 2)
        y = rng.randint(2, H - 2)
        r = rng.choice([0.6, 0.8, 1.0, 1.2])
        op = rng.uniform(0.3, 0.9)
        out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" opacity="{op:.2f}"/>')
    return "".join(out)


def _node(x: int, y: int, label: str, color: str, r: int = 30, alpha: float = 1.0) -> str:
    text = label[:10].upper()
    return (
        f'<g opacity="{alpha}">'
        f'<circle cx="{x}" cy="{y}" r="{r+8}" fill="none" '
        f'stroke="{color}" stroke-width="1.2" opacity="0.25" filter="url(#glow)"/>'
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="#0a0f1e" '
        f'stroke="{color}" stroke-width="2" filter="url(#glow)"/>'
        f'<circle cx="{x}" cy="{y}" r="{r-8}" fill="none" '
        f'stroke="{color}" stroke-width="0.6" opacity="0.4"/>'
        f'<text x="{x}" y="{y+r+14}" fill="{color}" font-size="10" '
        f'font-family="\'Courier New\',monospace" text-anchor="middle" '
        f'filter="url(#glow)">{text}</text>'
        f'</g>'
    )


def _line(x1: float, y1: float, x2: float, y2: float, color: str, dash: bool = False) -> str:
    da = ' stroke-dasharray="5,4"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="1.2" opacity="0.5" filter="url(#glow)"{da}/>'
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="0.4" opacity="0.8"{da}/>'
    )


def _particles(x1: float, y1: float, x2: float, y2: float, color: str, seed: str) -> str:
    rng = random.Random(seed)
    out = []
    for _ in range(4):
        t = rng.uniform(0.2, 0.8)
        px = x1 + (x2 - x1) * t + rng.uniform(-4, 4)
        py = y1 + (y2 - y1) * t + rng.uniform(-4, 4)
        r = rng.uniform(1.2, 2.5)
        out.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" '
            f'fill="{color}" opacity="0.7" filter="url(#glow)"/>'
        )
    return "".join(out)


def _ring_positions(count: int, rx: int, ry: int, angle_offset: int = -90) -> list:
    """Return [(x, y), ...] evenly distributed on ellipse around (CX, CY)."""
    if count == 0:
        return []
    positions = []
    for i in range(count):
        angle = math.radians(360 / count * i + angle_offset)
        x = CX + rx * math.cos(angle)
        y = CY + ry * math.sin(angle)
        positions.append((x, y))
    return positions


def _skill_color(skill_id: str, fallback_idx: int) -> str:
    return LANG_COLOR.get(skill_id, PALETTE[fallback_idx % len(PALETTE)])


# ── SVG chrome ────────────────────────────────────────────
_SVG_DEFS = """<defs>
<radialGradient id="bg" cx="50%" cy="50%" r="70%">
<stop offset="0%" stop-color="#0d1117"/>
<stop offset="100%" stop-color="#020409"/>
</radialGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
<feGaussianBlur stdDeviation="3" result="blur"/>
<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
</defs>"""


def _center_node(username: str, repos: int, followers: int) -> str:
    return (
        f'<g>'
        f'<circle cx="{CX}" cy="{CY}" r="{R_CENTER}" fill="#0a0f1e" '
        f'stroke="{ACCENT}" stroke-width="2.5" filter="url(#glow)"/>'
        f'<circle cx="{CX}" cy="{CY}" r="40" fill="none" '
        f'stroke="{ACCENT}" stroke-width="0.8" opacity="0.4"/>'
        f'<circle cx="{CX}" cy="{CY}" r="32" fill="none" '
        f'stroke="{ACCENT}" stroke-width="0.4" opacity="0.2"/>'
        f'<text x="{CX}" y="{CY-8}" fill="{ACCENT}" font-size="12" '
        f'font-family="\'Courier New\',monospace" text-anchor="middle" '
        f'font-weight="bold" filter="url(#glow)">@{username[:12]}</text>'
        f'<text x="{CX}" y="{CY+8}" fill="{SECONDARY}" font-size="9" '
        f'font-family="\'Courier New\',monospace" text-anchor="middle">{repos} repos</text>'
        f'<text x="{CX}" y="{CY+20}" fill="{SECONDARY}" font-size="9" '
        f'font-family="\'Courier New\',monospace" text-anchor="middle">{followers} followers</text>'
        f'</g>'
    )


def _title() -> str:
    return (
        f'<text x="{W//2}" y="36" fill="{ACCENT}" font-size="18" '
        f'font-family="\'Courier New\',monospace" text-anchor="middle" '
        f'font-weight="bold" letter-spacing="4" filter="url(#glow)">GITHUB SKILL TREE</text>'
        f'<text x="{W//2}" y="56" fill="#64748b" font-size="10" '
        f'font-family="\'Courier New\',monospace" text-anchor="middle">'
        f'CURRENT SKILLS  ---  RECOMMENDED NEXT</text>'
    )


def _legend() -> str:
    return (
        f'<circle cx="30" cy="{H-20}" r="5" fill="{ACCENT}" filter="url(#glow)"/>'
        f'<text x="40" y="{H-15}" fill="#475569" font-size="9" '
        f'font-family="monospace">Current Skills</text>'
        f'<circle cx="130" cy="{H-20}" r="5" fill="{REC_COLOR}" opacity="0.85" filter="url(#glow)"/>'
        f'<text x="140" y="{H-15}" fill="#475569" font-size="9" '
        f'font-family="monospace">Recommended</text>'
        f'<text x="{W-10}" y="{H-15}" fill="#1e293b" font-size="8" '
        f'font-family="monospace" text-anchor="end">github-skillstree.zeabur.app</text>'
    )


def _frame(body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">{_SVG_DEFS}'
        f'<rect width="{W}" height="{H}" rx="14" fill="url(#bg)"/>'
        f'{body}'
        f'<rect width="{W}" height="{H}" rx="14" fill="none" '
        f'stroke="{ACCENT}" stroke-width="1" opacity="0.3" filter="url(#glow)"/>'
        f'</svg>'
    )


# ── Public renderers ──────────────────────────────────────
def render_card(data: dict) -> str:
    """Render the full skill tree card from fetched data."""
    if not data:
        return render_error("User not found")

    skills = data["top_skills"][:7]
    recs = data["recommended"][:5]
    username = data["username"]

    inner = _ring_positions(len(skills), RX_INNER, RY_INNER, angle_offset=-90)
    outer = _ring_positions(len(recs), RX_OUTER, RY_OUTER, angle_offset=-70)

    parts = [_stars(username)]

    # Lines: center -> inner, inner -> outer (dashed)
    for i, ((x, y), (sid, _)) in enumerate(zip(inner, skills)):
        color = _skill_color(sid, i)
        parts.append(_line(CX, CY, x, y, color))
        parts.append(_particles(CX, CY, x, y, color, f"{username}{sid}"))

    for j, ((x2, y2), rid) in enumerate(zip(outer, recs)):
        if not inner:
            break
        x1, y1 = inner[j % len(inner)]
        parts.append(_line(x1, y1, x2, y2, REC_COLOR, dash=True))
        parts.append(_particles(x1, y1, x2, y2, REC_COLOR, f"rec{rid}"))

    parts.append(_title())
    parts.append(_center_node(username, data["repos"], data["followers"]))

    # Nodes (drawn on top of lines)
    for i, ((x, y), (sid, _)) in enumerate(zip(inner, skills)):
        parts.append(_node(int(x), int(y), sid, _skill_color(sid, i), r=R_SKILL))
    for (x, y), rid in zip(outer, recs):
        parts.append(_node(int(x), int(y), rid, REC_COLOR, r=R_REC, alpha=0.85))

    parts.append(_legend())
    return _frame("".join(parts))


def render_loading(username: str) -> str:
    """Shown on cold cache while background fetch runs."""
    body = (
        f'<text x="{W//2}" y="160" fill="{ACCENT}" font-size="18" '
        f'font-family="\'Courier New\',monospace" text-anchor="middle" '
        f'font-weight="bold" letter-spacing="4" filter="url(#glow)">GITHUB SKILL TREE</text>'
        f'<text x="{W//2}" y="200" fill="{SECONDARY}" font-size="13" '
        f'font-family="\'Courier New\',monospace" text-anchor="middle" '
        f'filter="url(#glow)">@{username[:20]}</text>'
        f'<text x="{W//2}" y="235" fill="#475569" font-size="11" '
        f'font-family="\'Courier New\',monospace" text-anchor="middle">'
        f'Analyzing repositories...</text>'
        f'<text x="{W//2}" y="265" fill="#1e3a2f" font-size="10" '
        f'font-family="monospace" text-anchor="middle">Refresh in a few seconds</text>'
    )
    return _frame(body)


def render_error(msg: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="100">'
        f'<rect width="500" height="100" rx="12" fill="#020409" '
        f'stroke="#ef4444" stroke-width="1"/>'
        f'<text x="250" y="55" fill="#ef4444" font-size="14" '
        f'font-family="monospace" text-anchor="middle">{msg}</text>'
        f'</svg>'
    )
