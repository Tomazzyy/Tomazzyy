"""Gera assets/stats.svg com dados reais do GitHub. Usa apenas a biblioteca padrão."""
import datetime as dt
import html
import json
import os
import pathlib
import re
import urllib.request

USER = "Tomazzyy"
OUTPUT = pathlib.Path(__file__).resolve().parent.parent / "assets" / "stats.svg"
LEVELS = ["#161c35", "#0b5c78", "#00a9c4", "#7f5cff", "#ff00ff"]
BARS = ["#00f7ff", "#35c8ff", "#7f5cff", "#c04dff", "#ff00ff"]


def fetch(url, api=True):
    headers = {"User-Agent": USER}
    token = os.environ.get("GITHUB_TOKEN")
    if api and token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return response.read().decode("utf-8")


def api(path):
    return json.loads(fetch(f"https://api.github.com/{path}"))


def contributions():
    page = fetch(f"https://github.com/users/{USER}/contributions", api=False)
    total = re.search(r"([\d,.]+)\s+contributions?\s+in the last year", page)
    days = {}
    for tag in re.findall(r"<td[^>]*data-date=[^>]*>", page):
        date = re.search(r'data-date="([\d-]+)"', tag)
        level = re.search(r'data-level="(\d)"', tag)
        if date and level:
            days[date.group(1)] = int(level.group(1))
    if not total or not days:
        raise RuntimeError("Formato da página de contribuições mudou")
    return int(re.sub(r"\D", "", total.group(1))), dict(sorted(days.items()))


def languages(repos):
    totals = {}
    for repo in repos:
        for name, size in api(f"repos/{repo['full_name']}/languages").items():
            totals[name] = totals.get(name, 0) + size
    grand_total = sum(totals.values()) or 1
    top = sorted(totals.items(), key=lambda item: -item[1])[:5]
    return [(name, size / grand_total * 100) for name, size in top]


def tile(x, y, label, value):
    return (
        f'<rect x="{x}" y="{y}" width="222" height="82" rx="8" fill="#10152b" stroke="#27304f"/>'
        f'<text class="num" x="{x + 16}" y="{y + 44}">{value:,}</text>'
        f'<text class="lab" x="{x + 16}" y="{y + 66}">{label}</text>'.replace(",", ".")
    )


def render(user, repos, langs, total, days):
    stars = sum(repo["stargazers_count"] for repo in repos)
    tiles = [
        tile(30, 66, "REPOSITÓRIOS", user["public_repos"]),
        tile(264, 66, "CONTRIBUIÇÕES/ANO", total),
        tile(30, 160, "SEGUIDORES", user["followers"]),
        tile(264, 160, "ESTRELAS", stars),
    ]

    bars = []
    for index, (name, percent) in enumerate(langs):
        y = 66 + index * 35
        color = BARS[index % len(BARS)]
        width = max(percent / 100 * 296, 4)
        bars.append(
            f'<text class="lang" x="524" y="{y + 16}">{html.escape(name)}</text>'
            f'<rect x="634" y="{y + 5}" width="296" height="12" rx="3" fill="#161c35"/>'
            f'<rect class="bar" style="animation-delay:{index * .15:.2f}s" x="634" y="{y + 5}" width="{width:.1f}" height="12" rx="3" fill="{color}"/>'
            f'<text class="pct" x="970" y="{y + 16}">{percent:.0f}%</text>'
        )

    first = dt.date.fromisoformat(next(iter(days)))
    offset = (first.weekday() + 1) % 7
    cells = []
    for date, level in days.items():
        index = (dt.date.fromisoformat(date) - first).days + offset
        x = 50 + index // 7 * 17
        y = 298 + index % 7 * 17
        cells.append(f'<rect x="{x}" y="{y}" width="14" height="14" rx="3" fill="{LEVELS[level]}"/>')

    today = dt.datetime.now(dt.timezone.utc).strftime("%d/%m/%Y")
    label = (
        f"{user['public_repos']} repositórios, {total} contribuições no último ano, "
        f"{user['followers']} seguidores. Linguagens: " + ", ".join(name for name, _ in langs)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 460" width="1000" height="460" role="img" aria-label="{html.escape(label)}">
  <defs>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#00f7ff"/><stop offset=".5" stop-color="#7f5cff"/><stop offset="1" stop-color="#ff00ff"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: 'JetBrains Mono', 'Fira Code', Consolas, Menlo, 'DejaVu Sans Mono', monospace; }}
    .head {{ font-size: 13px; letter-spacing: 4px; fill: #00f7ff; }}
    .num {{ font-size: 31px; font-weight: 800; fill: #fff; }}
    .lab {{ font-size: 11px; letter-spacing: 2px; fill: #8b97b8; }}
    .lang {{ font-size: 14px; fill: #d6e2ff; }}
    .pct {{ font-size: 13px; fill: #8b97b8; text-anchor: end; }}
    .sync {{ font-size: 11px; letter-spacing: 1px; fill: #6d7a9c; text-anchor: end; }}
    .bar {{ transform-box: fill-box; transform-origin: left; animation: grow 1.2s ease-out both; }}
    @keyframes grow {{ from {{ transform: scaleX(0); }} }}
    .sweep {{ animation: sweep 6s linear infinite; }}
    @keyframes sweep {{ from {{ transform: translateX(-20px); }} to {{ transform: translateX(930px); }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
  </style>
  <rect x="1" y="1" width="998" height="458" rx="14" fill="#0a0e1f" stroke="url(#edge)" stroke-width="1.5"/>
  <text class="head" x="30" y="46">// TELEMETRIA</text>
  <text class="head" x="524" y="46">// LINGUAGENS</text>
  {''.join(tiles)}
  {''.join(bars)}
  <text class="head" x="30" y="282">// ATIVIDADE_12_MESES</text>
  <text class="sync" x="970" y="282">SINCRONIZADO EM {today}</text>
  {''.join(cells)}
  <clipPath id="grid"><rect x="46" y="294" width="908" height="128"/></clipPath>
  <g clip-path="url(#grid)"><rect class="sweep" x="46" y="294" width="20" height="128" fill="#00f7ff" opacity=".28"/></g>
</svg>
"""


def main():
    user = api(f"users/{USER}")
    repos = [
        repo
        for repo in api(f"users/{USER}/repos?per_page=100")
        if not repo["fork"]
    ]
    total, days = contributions()
    OUTPUT.write_text(render(user, repos, languages(repos), total, days), encoding="utf-8")


if __name__ == "__main__":
    main()
