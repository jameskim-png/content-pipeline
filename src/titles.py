"""Title overlay: presets, HTML preview, and FFmpeg burn-in."""

import subprocess
import textwrap
from pathlib import Path

from .config import FONTS_DIR


# --- Title Presets ---

TITLE_PRESETS = {
    "clean": {
        "label": "클린 — 흰색, 깔끔한 스트로크",
        "font_file": "Pretendard-Bold.otf",
        "fontsize": 68,
        "fontcolor": "white",
        "borderw": 6,
        "bordercolor": "black",
        "box": False,
        "shadow": False,
        "y": 370,
    },
    "impact": {
        "label": "임팩트 — 노란색, 강렬한 느낌",
        "font_file": "Pretendard-ExtraBold.otf",
        "fontsize": 74,
        "fontcolor": "#FFD700",
        "borderw": 7,
        "bordercolor": "black",
        "box": False,
        "shadow": True,
        "y": 370,
    },
    "box": {
        "label": "박스 — 흰색, 배경 박스",
        "font_file": "Pretendard-Bold.otf",
        "fontsize": 66,
        "fontcolor": "white",
        "borderw": 0,
        "bordercolor": "black",
        "box": True,
        "shadow": False,
        "y": 370,
    },
}


def _wrap_title_text(text: str, fontsize: int, max_width: int = 960) -> list[str]:
    """Split title text into lines that fit within max_width pixels.

    Uses approximate character widths:
    - Korean (CJK): fontsize * 0.9
    - ASCII: fontsize * 0.5

    Line break priority: space > josa boundary > character boundary.
    max_width default: 1080 - 120 (60px padding each side) = 960px.
    """
    cjk_width = fontsize * 0.9
    ascii_width = fontsize * 0.5

    def _char_width(ch: str) -> float:
        if ord(ch) > 0x2E80:  # CJK range
            return cjk_width
        return ascii_width

    def _text_width(s: str) -> float:
        return sum(_char_width(c) for c in s)

    # If it fits in one line, no wrap needed
    if _text_width(text) <= max_width:
        return [text]

    # Try breaking at spaces first
    words = text.split(" ")
    if len(words) > 1:
        lines = []
        current = words[0]
        for word in words[1:]:
            candidate = current + " " + word
            if _text_width(candidate) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)

        # Check all lines fit
        if all(_text_width(line) <= max_width for line in lines):
            return lines

    # Fallback: character-level wrapping
    lines = []
    current = ""
    for ch in text:
        if _text_width(current + ch) > max_width:
            lines.append(current)
            current = ch
        else:
            current += ch
    if current:
        lines.append(current)

    return lines


def _build_drawtext_filter(
    title_text: str,
    preset_name: str,
    duration: str = "full",
    video_duration: float | None = None,
) -> str:
    """Build FFmpeg drawtext filter string for a given preset.

    Automatically wraps long titles into multiple lines, each rendered
    as a separate chained drawtext filter.

    duration: "full" (entire video) or "intro" (first 5s + 0.5s fade-out).
    video_duration: total video length in seconds (used for enable expression).
    """
    preset = TITLE_PRESETS[preset_name]
    font_path = FONTS_DIR / preset["font_file"]
    fontsize = preset["fontsize"]
    base_y = preset["y"]
    line_height = int(fontsize * 1.4)

    # Wrap text into lines
    lines = _wrap_title_text(title_text, fontsize)

    # Build one drawtext per line
    drawtext_filters = []
    for i, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("'", "'\\''").replace(":", "\\:")
        y = base_y + i * line_height

        parts = [
            f"fontfile='{font_path}'",
            f"text='{escaped}'",
            f"fontsize={fontsize}",
            f"fontcolor={preset['fontcolor']}",
            f"x=(w-text_w)/2",
            f"y={y}",
        ]

        if preset["borderw"] > 0:
            parts.append(f"borderw={preset['borderw']}")
            parts.append(f"bordercolor={preset['bordercolor']}")

        if preset["box"]:
            parts.append("box=1")
            parts.append("boxcolor=black@0.8")
            parts.append("boxborderw=20")

        if preset["shadow"]:
            parts.append("shadowcolor=black@0.6")
            parts.append("shadowx=3")
            parts.append("shadowy=3")

        if duration == "intro":
            parts.append("enable='between(t,0,5.5)'")
            parts.append("alpha='if(lt(t,5),1,(5.5-t)/0.5)'")

        drawtext_filters.append("drawtext=" + ":".join(parts))

    return ",".join(drawtext_filters)


def burn_title(
    video_path: Path,
    title_text: str,
    preset_name: str,
    output_path: Path,
    duration: str = "full",
) -> Path:
    """Burn title overlay onto video using FFmpeg drawtext.

    preset_name: "clean", "impact", or "box".
    duration: "full" (default) or "intro" (first 5s + fade-out).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    filter_str = _build_drawtext_filter(title_text, preset_name, duration)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def generate_title_preview_html(
    title_text: str,
    output_path: Path,
    subtitle_sample: str = "이건 자막 위치 샘플이에요",
    subtitle_styles: dict | None = None,
) -> Path:
    """Generate an HTML preview page showing all 3 title presets.

    Renders 1080x1920 actual-pixel frames (scaled to fit screen) per preset,
    with title at the top and subtitle sample at the bottom to show real layout.

    If subtitle_styles is provided (dict of name -> style with preview_css),
    renders an additional section showing subtitle style previews.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build preset cards
    cards_html = ""
    for i, (name, preset) in enumerate(TITLE_PRESETS.items(), 1):
        font_weight = "800" if "ExtraBold" in preset["font_file"] else "700"
        color = preset["fontcolor"] if preset["fontcolor"] != "white" else "#FFFFFF"

        # Title text style (px values = actual 1080x1920 pixels)
        title_styles = [
            f"color: {color}",
            f"font-size: {preset['fontsize']}px",
            f"font-weight: {font_weight}",
            "font-family: 'Pretendard', sans-serif",
            "text-align: center",
            "max-width: 90%",
            "word-break: keep-all",
            "line-height: 1.3",
        ]

        if preset["borderw"] > 0:
            sw = preset["borderw"]
            title_styles.append(
                f"text-shadow: -{sw}px -{sw}px 0 black, {sw}px -{sw}px 0 black, "
                f"-{sw}px {sw}px 0 black, {sw}px {sw}px 0 black"
            )

        if preset["shadow"]:
            existing = next((s for s in title_styles if s.startswith("text-shadow")), None)
            if existing:
                title_styles.remove(existing)
                title_styles.append(existing + ", 4px 4px 8px rgba(0,0,0,0.6)")
            else:
                title_styles.append("text-shadow: 4px 4px 8px rgba(0,0,0,0.6)")

        box_styles = ""
        if preset["box"]:
            box_styles = "background: rgba(0,0,0,0.8); padding: 16px 32px; border-radius: 12px;"

        title_style_str = "; ".join(title_styles)

        # Subtitle style: box preset gets background box on subtitle too
        sub_extra = ""
        if preset["box"]:
            sub_extra = "background: rgba(0,0,0,0.8); padding: 10px 28px; border-radius: 8px;"

        cards_html += f"""
        <div class="card">
          <div class="label">{i}. {preset['label']}</div>
          <div class="frame">
            <div class="title-area">
              <span class="title-text" style="{title_style_str}; {box_styles}">{title_text}</span>
            </div>
            <div class="subtitle-area">
              <span class="subtitle-text" style="{sub_extra}">{subtitle_sample}</span>
            </div>
            <div class="guide guide-title">TITLE Y:{preset['y']}px</div>
            <div class="guide guide-subtitle">SUBTITLE MarginV:480</div>
          </div>
        </div>
        """

    # Build subtitle style cards (if provided)
    subtitle_cards_html = ""
    if subtitle_styles:
        for j, (sname, sstyle) in enumerate(subtitle_styles.items(), 1):
            css = sstyle.get("preview_css", {})
            sub_style_parts = [
                "font-family: Arial, sans-serif",
                f"color: {css.get('color', '#FFFFFF')}",
                f"font-size: {css.get('font_size', '48px')}",
                f"font-weight: {css.get('font_weight', '700')}",
                "text-align: center",
            ]
            ts = css.get("text_shadow", "none")
            if ts and ts != "none":
                sub_style_parts.append(f"text-shadow: {ts}")
            bg = css.get("background", "none")
            extra_box = ""
            if bg and bg != "none":
                extra_box = f"background: {bg};"
                if "padding" in css:
                    extra_box += f" padding: {css['padding']};"
                if "border_radius" in css:
                    extra_box += f" border-radius: {css['border_radius']};"

            sub_css_str = "; ".join(sub_style_parts)
            label = sstyle.get("label", sname)

            subtitle_cards_html += f"""
        <div class="card">
          <div class="label">{j}. {label}</div>
          <div class="frame">
            <div class="subtitle-area">
              <span style="{sub_css_str}; {extra_box}">{subtitle_sample}</span>
            </div>
            <div class="guide guide-subtitle">SUBTITLE MarginV:480</div>
          </div>
        </div>
            """

    # Subtitle section header
    subtitle_section_html = ""
    if subtitle_cards_html:
        subtitle_section_html = f"""
      <h1 style="margin-top: 48px;">자막 스타일 미리보기</h1>
      <div class="spec">선택 가능한 자막 스타일</div>
      {subtitle_cards_html}
        """

    html = textwrap.dedent(f"""\
    <!DOCTYPE html>
    <html lang="ko">
    <head>
      <meta charset="UTF-8">
      <title>Title + Subtitle Preview — 1080x1920 실제 비율</title>
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.min.css">
      <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
          background: #111;
          color: #fff;
          font-family: 'Pretendard', sans-serif;
          display: flex;
          flex-wrap: wrap;
          justify-content: center;
          gap: 40px;
          padding: 40px 20px;
        }}
        h1 {{
          width: 100%;
          text-align: center;
          font-size: 22px;
          margin-bottom: 4px;
        }}
        .spec {{
          width: 100%;
          text-align: center;
          font-size: 13px;
          color: #666;
          margin-bottom: 12px;
        }}
        .card {{
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
        }}
        .label {{
          font-size: 16px;
          font-weight: 700;
          color: #ccc;
        }}
        /* 1080x1920 actual pixels, scaled down via transform to fit screen */
        .frame {{
          width: 1080px;
          height: 1920px;
          border-radius: 40px;
          overflow: hidden;
          position: relative;
          background: linear-gradient(180deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
          transform: scale(0.25);
          transform-origin: top center;
          margin-bottom: -1440px;  /* compensate for scale */
        }}
        /* Title position: Y=370px from top, centered */
        .title-area {{
          position: absolute;
          top: 370px;
          left: 0;
          right: 0;
          display: flex;
          justify-content: center;
        }}
        /* Subtitle position: bottom, MarginV=480px, ASS Alignment=2 */
        .subtitle-area {{
          position: absolute;
          bottom: 480px;
          left: 20px;
          right: 20px;
          display: flex;
          justify-content: center;
        }}
        .subtitle-text {{
          font-family: Arial, sans-serif;
          font-size: 48px;
          font-weight: 700;
          color: #FFFFFF;
          text-shadow: -4px -4px 0 black, 4px -4px 0 black, -4px 4px 0 black, 4px 4px 0 black,
                       -4px 0 0 black, 4px 0 0 black, 0 -4px 0 black, 0 4px 0 black;
          text-align: center;
        }}
        /* Guide labels */
        .guide {{
          position: absolute;
          font-size: 24px;
          color: rgba(255,255,255,0.3);
          font-weight: 400;
          pointer-events: none;
        }}
        .guide-title {{
          top: 310px;
          right: 30px;
        }}
        .guide-subtitle {{
          bottom: 550px;
          right: 30px;
        }}
      </style>
    </head>
    <body>
      <h1>타이틀 + 자막 미리보기</h1>
      <div class="spec">1080 x 1920px 실제 비율 (25% 축소) &mdash; 타이틀 상단 / 자막 하단</div>
      {cards_html}
      {subtitle_section_html}
    </body>
    </html>
    """)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
