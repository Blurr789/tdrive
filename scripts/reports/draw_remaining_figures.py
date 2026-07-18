from __future__ import annotations

import html
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "outputs" / "beijing_tdrive"
FIGURES = ROOT / "reports" / "figures"


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def write_svg(path: Path, body: str, width: int = 1400, height: int = 850) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <style>
      .title {{ font-family: SimHei, SimSun, sans-serif; font-size: 34px; font-weight: 700; fill: #111827; }}
      .subtitle {{ font-family: SimSun, serif; font-size: 19px; fill: #4b5563; }}
      .label {{ font-family: SimSun, serif; font-size: 20px; fill: #111827; }}
      .small {{ font-family: SimSun, serif; font-size: 16px; fill: #374151; }}
      .tiny {{ font-family: "Times New Roman", SimSun, serif; font-size: 14px; fill: #4b5563; }}
      .en {{ font-family: "Times New Roman", serif; }}
    </style>
    <marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" markerUnits="strokeWidth">
      <path d="M2,2 L10,6 L2,10 Z" fill="#b45309" />
    </marker>
    <linearGradient id="warm" x1="0%" x2="100%" y1="0%" y2="0%">
      <stop offset="0%" stop-color="#fef3c7"/>
      <stop offset="50%" stop-color="#fb923c"/>
      <stop offset="100%" stop-color="#b91c1c"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="#111827" flood-opacity="0.16"/>
    </filter>
  </defs>
  <rect width="100%" height="100%" fill="#ffffff"/>
{body}
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def box(x: int, y: int, w: int, h: int, title: str, lines: list[str], fill: str = "#fff7ed") -> str:
    line_svg = []
    for index, line in enumerate(lines):
        line_svg.append(f'<text class="small" x="{x + 28}" y="{y + 78 + index * 28}">{esc(line)}</text>')
    return f"""
  <g filter="url(#shadow)">
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="{fill}" stroke="#fed7aa" stroke-width="2"/>
    <text class="label" x="{x + 28}" y="{y + 42}" font-weight="700">{esc(title)}</text>
    {''.join(line_svg)}
  </g>
"""


def arrow(x1: int, y1: int, x2: int, y2: int) -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#b45309" stroke-width="4" marker-end="url(#arrow)"/>'


def draw_hex_grid(cx: int, cy: int) -> str:
    cells = []
    radius = 42
    offsets = [(0, 0), (74, 0), (-74, 0), (37, 64), (-37, 64), (37, -64), (-37, -64)]
    for i, (dx, dy) in enumerate(offsets):
        x = cx + dx
        y = cy + dy
        points = []
        for k in range(6):
            angle = 3.1415926 / 6 + k * 3.1415926 / 3
            points.append((x + radius * __import__("math").cos(angle), y + radius * __import__("math").sin(angle)))
        point_text = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
        fill = "#fee2e2" if i == 0 else "#ffedd5"
        stroke = "#b91c1c" if i == 0 else "#fdba74"
        cells.append(f'<polygon points="{point_text}" fill="{fill}" stroke="{stroke}" stroke-width="{3 if i == 0 else 1.5}"/>')
    cells.append(f'<circle cx="{cx}" cy="{cy}" r="7" fill="#b91c1c"/>')
    return f"<g>{''.join(cells)}</g>"


def figure_2() -> None:
    body = f"""
  <text class="title" x="70" y="70">图2 H3 网格与高德逆地理编码地名增强示意图</text>
  <text class="subtitle" x="70" y="108">将抽象 H3 编号转换为可读的北京街道、商圈和 POI 语义名称</text>
  {box(70, 170, 270, 190, "轨迹活动段", ["活动起点 / 活动终点", "经纬度坐标 GCJ-02", "夜间 20:00-03:00"], "#f8fafc")}
  {arrow(350, 265, 460, 265)}
  {box(470, 170, 270, 190, "H3 空间聚合", ["resolution 7", "生成活动网格", "统计活动强度"], "#fff7ed")}
  {arrow(750, 265, 860, 265)}
  {box(870, 170, 360, 190, "高德逆地理编码", ["网格中心点 → 地址解析", "区县 / 街道 / 商圈", "附近 POI / AOI"], "#fef2f2")}
  {arrow(1045, 370, 1045, 470)}
  {box(830, 480, 430, 220, "可解释网格名称", ["示例：朝阳区 · 大屯街道", "示例：顺义区 · 空港街道", "示例：海淀区 · 学院路街道", "用于地图标签、搜索和报告分析"], "#ffffff")}
  {draw_hex_grid(325, 575)}
  <text class="label" x="190" y="735">H3 活动网格</text>
  <rect x="500" y="500" width="230" height="138" rx="18" fill="#111827"/>
  <text class="small" x="528" y="540" fill="#ffffff">grid_name_lookup</text>
  <text class="tiny" x="528" y="572" fill="#e5e7eb">spatial_unit</text>
  <text class="tiny" x="528" y="598" fill="#e5e7eb">display_name</text>
  <text class="tiny" x="528" y="624" fill="#e5e7eb">poi / aoi / adcode</text>
  {arrow(430, 575, 490, 575)}
  {arrow(735, 575, 820, 575)}
  <text class="subtitle" x="82" y="810">方法作用：既保留 H3 网格的统一空间表达，又让前端和报告能够显示真实北京地名。</text>
"""
    write_svg(FIGURES / "图2_H3网格与高德逆地理编码地名增强示意图.svg", body)


def load_top_data(limit: int = 6):
    scores = pd.read_csv(OUTPUT / "region_scores_phase2.csv")
    scores["spatial_unit"] = scores["spatial_unit"].astype(str)
    names = pd.read_csv(OUTPUT / "grid_name_lookup.csv")
    names["spatial_unit"] = names["spatial_unit"].astype(str)
    scores = scores.merge(names[["spatial_unit", "display_name"]], on="spatial_unit", how="left")
    top = scores.sort_values("night_vitality_score", ascending=False).head(limit)
    hourly = pd.read_csv(OUTPUT / "hourly_activity.csv")
    hourly["spatial_unit"] = hourly["spatial_unit"].astype(str)
    return top, hourly


def figure_7() -> None:
    top, hourly = load_top_data()
    hours = [20, 21, 22, 23, 0, 1, 2, 3]
    chart_x, chart_y, chart_w, chart_h = 90, 155, 850, 430
    bar_x, bar_y, bar_w, bar_h = 1020, 155, 270, 430
    colors = ["#b91c1c", "#ea580c", "#d97706", "#f97316", "#92400e", "#7c2d12"]

    series = []
    max_value = 1
    for _, row in top.iterrows():
        unit = row["spatial_unit"]
        grouped = hourly[hourly["spatial_unit"] == unit].groupby("hour")["activity_count"].sum()
        values = [int(grouped.get(hour, 0)) for hour in hours]
        max_value = max(max_value, max(values))
        series.append((row, values))

    def px(i: int) -> float:
        return chart_x + i * chart_w / (len(hours) - 1)

    def py(value: float) -> float:
        return chart_y + chart_h - value / max_value * chart_h

    grid = []
    for step in range(5):
        value = max_value * step / 4
        y = py(value)
        grid.append(f'<line x1="{chart_x}" y1="{y:.1f}" x2="{chart_x + chart_w}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
        grid.append(f'<text class="tiny" x="{chart_x - 52}" y="{y + 5:.1f}">{int(value)}</text>')
    for i, hour in enumerate(hours):
        x = px(i)
        grid.append(f'<line x1="{x:.1f}" y1="{chart_y}" x2="{x:.1f}" y2="{chart_y + chart_h}" stroke="#f3f4f6" stroke-width="1"/>')
        grid.append(f'<text class="tiny" x="{x - 14:.1f}" y="{chart_y + chart_h + 32}">{hour}:00</text>')

    lines = []
    legend = []
    for index, (row, values) in enumerate(series):
        points = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(values))
        color = colors[index % len(colors)]
        lines.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>')
        for i, value in enumerate(values):
            lines.append(f'<circle cx="{px(i):.1f}" cy="{py(value):.1f}" r="5" fill="{color}" stroke="#fff" stroke-width="2"/>')
        name = str(row.get("display_name") or row["spatial_unit"])
        if len(name) > 14:
            name = name[:13] + "…"
        legend.append(f'<rect x="90" y="{635 + index * 30}" width="18" height="10" rx="5" fill="{color}"/>')
        legend.append(f'<text class="small" x="118" y="{646 + index * 30}">{esc(name)}（{float(row["night_vitality_score"]):.1f}）</text>')

    bars = []
    max_boost = max(float(row["weekend_boost"]) for _, row in top.iterrows())
    for index, (_, row) in enumerate(top.iterrows()):
        boost = float(row["weekend_boost"])
        h = boost / max_boost * (bar_h - 35)
        x = bar_x + index * (bar_w / len(top)) + 7
        y = bar_y + bar_h - h
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="30" height="{h:.1f}" rx="6" fill="#fb923c"/>')
        bars.append(f'<text class="tiny" x="{x - 2:.1f}" y="{bar_y + bar_h + 28}">Top{index + 1}</text>')
        bars.append(f'<text class="tiny" x="{x - 4:.1f}" y="{y - 8:.1f}">{boost:.2f}</text>')

    body = f"""
  <text class="title" x="70" y="70">图7 Top 活动网格小时变化与周末效应</text>
  <text class="subtitle" x="70" y="108">折线表示 20:00-03:00 各小时活动量，右侧柱状表示周末增幅</text>
  <rect x="{chart_x}" y="{chart_y}" width="{chart_w}" height="{chart_h}" fill="#ffffff" stroke="#d1d5db" stroke-width="2"/>
  {''.join(grid)}
  {''.join(lines)}
  <text class="label" x="{chart_x}" y="{chart_y - 22}">Top 网格小时活动量</text>
  <text class="small" x="{chart_x - 58}" y="{chart_y - 8}">活动量</text>
  <text class="small" x="{chart_x + chart_w - 20}" y="{chart_y + chart_h + 72}">小时</text>
  {''.join(legend)}
  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" fill="#fff7ed" stroke="#fed7aa" stroke-width="2" rx="14"/>
  <text class="label" x="{bar_x}" y="{bar_y - 22}">周末增幅</text>
  {''.join(bars)}
  <text class="subtitle" x="90" y="815">解读：高活力网格在晚间和深夜均保持较高活动量，周末增幅显示非工作日夜间需求继续放大。</text>
"""
    write_svg(FIGURES / "图7_Top网格小时变化与周末效应.svg", body)


def main() -> None:
    figure_2()
    figure_7()
    print(FIGURES)


if __name__ == "__main__":
    main()
