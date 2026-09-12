"""Tabler SVG icon provider using pytablericons."""

import re
from pathlib import Path
from typing import Any

import pytablericons
from pytablericons import OutlineIcon, TablerIcons

OUTLINE_DIR = Path(pytablericons.__file__).parent / "icons" / "outline"
FILLED_DIR = Path(pytablericons.__file__).parent / "icons" / "filled"

_SVG_CACHE: dict[str, str] = {}
_IMG_CACHE: dict[str, Any] = {}


def get_tabler_image(icon: OutlineIcon, size: int = 32):
    """Load a PIL Image suitable for Streamlit page_icon."""
    key = f"{icon.name}_{size}"
    if key in _IMG_CACHE:
        return _IMG_CACHE[key]
    try:
        img = TablerIcons.load(icon, size=size)
        _IMG_CACHE[key] = img
        return img
    except Exception:
        return None



def get_icon_svg(
    name: str,
    size: int = 18,
    color: str = "currentColor",
    stroke_width: float = 2.0,
    filled: bool = False,
    extra_style: str = "",
) -> str:
    """Load and format a clean Tabler SVG icon."""
    cache_key = f"{name}_{size}_{color}_{stroke_width}_{filled}_{extra_style}"
    if cache_key in _SVG_CACHE:
        return _SVG_CACHE[cache_key]

    target_dir = FILLED_DIR if filled else OUTLINE_DIR
    svg_path = target_dir / f"{name}.svg"

    if not svg_path.exists():
        # Fallback to outline if filled requested but not present
        svg_path = OUTLINE_DIR / f"{name}.svg"
        if not svg_path.exists():
            return ""

    try:
        raw = svg_path.read_text(encoding="utf-8")
        # Strip HTML comments
        raw = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)
        # Update width, height, stroke, stroke-width
        raw = re.sub(r'width="\d+"', f'width="{size}"', raw)
        raw = re.sub(r'height="\d+"', f'height="{size}"', raw)
        if not filled:
            raw = re.sub(r'stroke="currentColor"', f'stroke="{color}"', raw)
            raw = re.sub(r'stroke-width="[\d.]+"', f'stroke-width="{stroke_width}"', raw)

        style_attr = f'style="vertical-align: -3px; display: inline-block; margin-right: 5px; {extra_style}"'
        raw = raw.replace("<svg", f"<svg {style_attr}")
        rendered = raw.strip()
        _SVG_CACHE[cache_key] = rendered
        return rendered
    except Exception:
        return ""


def get_temp_badge(temperature: str) -> str:
    """Return executive temperature badge with Tabler SVG icons instead of emojis."""
    temp_upper = (temperature or "").upper()
    if temp_upper == "HOT":
        icon = get_icon_svg("flame", size=14, color="#f87171", extra_style="margin-right:4px;")
        return f'<span class="badge-hot">{icon}HOT</span>'
    elif temp_upper == "WARM":
        icon = get_icon_svg("bolt", size=14, color="#fb923c", extra_style="margin-right:4px;")
        return f'<span class="badge-warm">{icon}WARM</span>'
    elif temp_upper == "COOL":
        icon = get_icon_svg("sparkles", size=14, color="#facc15", extra_style="margin-right:4px;")
        return f'<span class="badge-cool">{icon}COOL</span>'
    elif temp_upper in ["COLD", "LOW"]:
        icon = get_icon_svg("snowflake", size=14, color="#60a5fa", extra_style="margin-right:4px;")
        return f'<span class="badge-cold">{icon}{temp_upper}</span>'
    else:
        icon = get_icon_svg("shield-check", size=14, color="#94a3b8", extra_style="margin-right:4px;")
        return f'<span class="badge-unqualified">{icon}{temp_upper or "REVIEW"}</span>'
