# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "figures"
PNG_PATH = OUT_DIR / "urban_nightsense_system_architecture.png"
SVG_PATH = OUT_DIR / "urban_nightsense_system_architecture.svg"

W, H = 1600, 760


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    if bold:
        candidates = [
            Path(r"C:\Windows\Fonts\msyhbd.ttc"),
            Path(r"C:\Windows\Fonts\simhei.ttf"),
            Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
            Path(r"C:\Windows\Fonts\simsun.ttc"),
        ]
    else:
        candidates = [
            Path(r"C:\Windows\Fonts\msyh.ttc"),
            Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
            Path(r"C:\Windows\Fonts\simhei.ttf"),
            Path(r"C:\Windows\Fonts\simsun.ttc"),
        ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


FONT_TITLE = load_font(44, True)
FONT_SUBTITLE = load_font(23)
FONT_BOX = load_font(30, True)
FONT_NOTE = load_font(21)
FONT_OUTPUT = load_font(24, True)

BLUE = "#2F80ED"
LIGHT_BLUE = "#EAF4FF"
DEEP_BLUE = "#173B68"
TEXT = "#1F2A37"
MUTED = "#5F6B7A"
LINE = "#7CAFE8"
BG = "#FFFFFF"


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def center_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
    y_offset: int = 0,
) -> None:
    x1, y1, x2, y2 = box
    tw, th = text_size(draw, text, font)
    draw.text(((x1 + x2 - tw) / 2, (y1 + y2 - th) / 2 + y_offset), text, font=font, fill=fill)


def draw_arrow(draw: ImageDraw.ImageDraw, x1: int, y: int, x2: int) -> None:
    draw.line((x1, y, x2 - 18, y), fill=LINE, width=5)
    draw.polygon([(x2, y), (x2 - 22, y - 13), (x2 - 22, y + 13)], fill=LINE)


def draw_box(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, title: str, note: str) -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=18, fill=LIGHT_BLUE, outline=BLUE, width=3)
    center_text(draw, (x, y + 18, x + w, y + 78), title, FONT_BOX, DEEP_BLUE)
    center_text(draw, (x + 18, y + 82, x + w - 18, y + h - 20), note, FONT_NOTE, MUTED)


def draw_png() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw.text((80, 70), "Urban NightSense 系统架构", font=FONT_TITLE, fill=TEXT)
    draw.text((82, 132), "从出行数据到夜间活力地图的分析流程", font=FONT_SUBTITLE, fill=MUTED)

    boxes = [
        ("数据输入", "出租车轨迹\n区域边界"),
        ("数据处理", "清洗匹配\n小时聚合"),
        ("活力分析", "活力评分\n异常识别"),
        ("服务接口", "API服务\n结果缓存"),
        ("前端展示", "高德地图\n报告输出"),
    ]

    x0, y0 = 82, 275
    bw, bh, gap = 240, 180, 72
    for index, (title, note) in enumerate(boxes):
        x = x0 + index * (bw + gap)
        draw_box(draw, x, y0, bw, bh, title, note)
        if index < len(boxes) - 1:
            draw_arrow(draw, x + bw + 18, y0 + bh // 2, x + bw + gap - 18)

    draw.rounded_rectangle((82, 565, 1518, 640), radius=16, fill="#F5FAFF", outline="#C8DEF8", width=2)
    draw.text((118, 590), "核心输出：夜间活力地图、区域画像、异常事件、可信度说明", font=FONT_OUTPUT, fill=DEEP_BLUE)

    img.save(PNG_PATH, quality=96)


def draw_svg() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    boxes = [
        ("数据输入", "出租车轨迹", "区域边界"),
        ("数据处理", "清洗匹配", "小时聚合"),
        ("活力分析", "活力评分", "异常识别"),
        ("服务接口", "API服务", "结果缓存"),
        ("前端展示", "高德地图", "报告输出"),
    ]

    parts: list[str] = []
    x0, y0 = 82, 275
    bw, bh, gap = 240, 180, 72
    for i, (title, note1, note2) in enumerate(boxes):
        x = x0 + i * (bw + gap)
        parts.append(f'<rect x="{x}" y="{y0}" width="{bw}" height="{bh}" rx="18" fill="{LIGHT_BLUE}" stroke="{BLUE}" stroke-width="3"/>')
        parts.append(f'<text x="{x + bw / 2}" y="{y0 + 70}" font-size="30" font-weight="700" fill="{DEEP_BLUE}" text-anchor="middle">{title}</text>')
        parts.append(f'<text x="{x + bw / 2}" y="{y0 + 118}" font-size="21" fill="{MUTED}" text-anchor="middle">{note1}</text>')
        parts.append(f'<text x="{x + bw / 2}" y="{y0 + 150}" font-size="21" fill="{MUTED}" text-anchor="middle">{note2}</text>')
        if i < len(boxes) - 1:
            sx = x + bw + 18
            ex = x + bw + gap - 18
            cy = y0 + bh // 2
            parts.append(f'<line x1="{sx}" y1="{cy}" x2="{ex - 18}" y2="{cy}" stroke="{LINE}" stroke-width="5"/>')
            parts.append(f'<polygon points="{ex},{cy} {ex - 22},{cy - 13} {ex - 22},{cy + 13}" fill="{LINE}"/>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <style>
    text {{ font-family: "Noto Sans SC", "Microsoft YaHei", "SimHei", sans-serif; letter-spacing: 0; }}
  </style>
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <text x="80" y="116" font-size="44" font-weight="700" fill="{TEXT}">Urban NightSense 系统架构</text>
  <text x="82" y="164" font-size="23" fill="{MUTED}">从出行数据到夜间活力地图的分析流程</text>
  {''.join(parts)}
  <rect x="82" y="565" width="1436" height="75" rx="16" fill="#F5FAFF" stroke="#C8DEF8" stroke-width="2"/>
  <text x="118" y="615" font-size="24" font-weight="700" fill="{DEEP_BLUE}">核心输出：夜间活力地图、区域画像、异常事件、可信度说明</text>
</svg>
'''
    SVG_PATH.write_text(svg, encoding="utf-8")


def main() -> None:
    draw_png()
    draw_svg()
    print(PNG_PATH)
    print(SVG_PATH)


if __name__ == "__main__":
    main()
