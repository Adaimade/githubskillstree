"""Pre-render skill tree SVG to a file (used by GitHub Actions)."""
import sys

from github_client import fetch_skill_tree
from svg_render import render_card, render_error


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: render_svg.py <username> <output.svg>", file=sys.stderr)
        return 1

    username = sys.argv[1]
    output_path = sys.argv[2]

    data = fetch_skill_tree(username)
    svg = render_card(data) if data else render_error(f"User {username} not found")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Wrote {output_path} ({len(svg)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
