#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the AOMT application icon.

The build script calls this file before Nuitka packaging. It creates a
multi-size Windows ICO plus a PNG preview for quick visual checks.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ICO_PATH = ROOT / "app.ico"
PREVIEW_PATH = ROOT / "app_icon_preview.png"
SELECTED_VARIANT = 4
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]


def _load_font(size: int, bold: bool = True):
    from PIL import ImageFont

    candidates = [
        r"C:\Windows\Fonts\seguisb.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\msyhbd.ttc",
    ]
    if not bold:
        candidates = [
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\msyh.ttc",
        ] + candidates

    for font_path in candidates:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size=size)

    return ImageFont.load_default()


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _gradient_color(x: int, y: int, size: int) -> tuple[int, int, int, int]:
    # Deep blue -> vivid indigo -> electric cyan. Modern but still business-like.
    t = (x * 0.7 + y * 0.3) / max(1, size - 1)
    if t < 0.55:
        k = t / 0.55
        c1 = (13, 71, 161)
        c2 = (70, 95, 255)
    else:
        k = (t - 0.55) / 0.45
        c1 = (70, 95, 255)
        c2 = (0, 188, 212)
    return (_lerp(c1[0], c2[0], k), _lerp(c1[1], c2[1], k), _lerp(c1[2], c2[2], k), 255)


def _text_bbox(draw, text: str, font):
    try:
        return draw.textbbox((0, 0), text, font=font)
    except AttributeError:
        w, h = draw.textsize(text, font=font)
        return (0, 0, w, h)


def _fit_font(draw, text: str, max_width: int, max_height: int, start_size: int):
    size = start_size
    while size > 8:
        font = _load_font(size, bold=True)
        left, top, right, bottom = _text_bbox(draw, text, font)
        if right - left <= max_width and bottom - top <= max_height:
            return font, (left, top, right, bottom)
        size -= 2
    font = _load_font(size, bold=True)
    return font, _text_bbox(draw, text, font)


def _draw_accent(draw, canvas: int, variant: int) -> None:
    stroke = max(12, int(canvas * 0.07))

    if variant == 1:
        draw.arc(
            [int(canvas * 0.15), int(canvas * 0.13), int(canvas * 0.86), int(canvas * 0.84)],
            start=205,
            end=28,
            fill=(255, 255, 255, 86),
            width=stroke,
        )
        draw.arc(
            [int(canvas * 0.25), int(canvas * 0.23), int(canvas * 0.98), int(canvas * 0.96)],
            start=198,
            end=303,
            fill=(255, 73, 145, 120),
            width=max(8, int(canvas * 0.045)),
        )
        draw.ellipse(
            [int(canvas * 0.72), int(canvas * 0.20), int(canvas * 0.82), int(canvas * 0.30)],
            fill=(255, 255, 255, 150),
        )
        return

    if variant == 2:
        path = [
            (int(canvas * 0.12), int(canvas * 0.72)),
            (int(canvas * 0.28), int(canvas * 0.42)),
            (int(canvas * 0.46), int(canvas * 0.48)),
            (int(canvas * 0.64), int(canvas * 0.27)),
            (int(canvas * 0.88), int(canvas * 0.37)),
        ]
        draw.line(path, fill=(255, 255, 255, 82), width=stroke, joint="curve")
        arc_box = [
            int(canvas * 0.07),
            int(canvas * 0.13),
            int(canvas * 0.63),
            int(canvas * 0.76),
        ]
        arc_parts = [
            (214, 238, int(canvas * 0.060), 92),
            (238, 262, int(canvas * 0.052), 108),
            (262, 286, int(canvas * 0.044), 124),
            (286, 310, int(canvas * 0.035), 138),
        ]
        for start, end, width, alpha in arc_parts:
            draw.arc(
                arc_box,
                start=start,
                end=end,
                fill=(255, 73, 145, alpha),
                width=max(5, width),
            )
        draw.line(path[2:], fill=(255, 255, 255, 86), width=max(8, int(canvas * 0.042)), joint="curve")
        pink_node = (int(canvas * 0.37), int(canvas * 0.63))
        for index, (x, y) in enumerate([pink_node, path[3], path[4]]):
            r = int(canvas * (0.037 if index != 1 else 0.047))
            fill = (255, 255, 255, 150) if index != 0 else (255, 73, 145, 145)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)
        return

    if variant == 4:
        left = (int(canvas * 0.30), int(canvas * 0.52))
        apex = (int(canvas * 0.50), int(canvas * 0.12))
        right = (int(canvas * 0.70), int(canvas * 0.52))
        cross_l = (int(canvas * 0.375), int(canvas * 0.39))
        cross_r = (int(canvas * 0.625), int(canvas * 0.39))
        main_w = max(10, int(canvas * 0.050))
        cross_w = max(8, int(canvas * 0.036))

        draw.line([cross_l, cross_r], fill=(174, 247, 224, 224), width=cross_w)
        draw.line([left, apex], fill=(220, 177, 92, 210), width=main_w, joint="curve")
        draw.line([apex, right], fill=(126, 232, 214, 210), width=main_w, joint="curve")

        for x, y, r, fill in [
            (*apex, int(canvas * 0.034), (232, 238, 222, 220)),
            (*left, int(canvas * 0.028), (220, 177, 92, 210)),
            (*right, int(canvas * 0.028), (126, 232, 214, 210)),
        ]:
            draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)
        return

    # Variant 3: diagonal layered signal, no upper arc.
    band_w = max(12, int(canvas * 0.064))
    draw.line(
        [(int(canvas * 0.10), int(canvas * 0.36)), (int(canvas * 0.88), int(canvas * 0.67))],
        fill=(255, 255, 255, 74),
        width=band_w,
    )
    draw.line(
        [(int(canvas * 0.18), int(canvas * 0.25)), (int(canvas * 0.65), int(canvas * 0.44))],
        fill=(255, 73, 145, 122),
        width=max(8, int(canvas * 0.046)),
    )
    draw.line(
        [(int(canvas * 0.36), int(canvas * 0.78)), (int(canvas * 0.86), int(canvas * 0.42))],
        fill=(255, 255, 255, 80),
        width=max(8, int(canvas * 0.048)),
    )
    for x, y, r, fill in [
        (int(canvas * 0.20), int(canvas * 0.25), int(canvas * 0.036), (255, 255, 255, 135)),
        (int(canvas * 0.72), int(canvas * 0.43), int(canvas * 0.048), (255, 73, 145, 126)),
        (int(canvas * 0.84), int(canvas * 0.66), int(canvas * 0.034), (255, 255, 255, 130)),
    ]:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _make_icon(size: int, variant: int = SELECTED_VARIANT):
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    scale = 4
    canvas = size * scale
    radius = int(canvas * 0.24)
    pad = max(2, int(canvas * 0.035))

    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Modern AOMT mark: a clean squircle, restrained neon gradient, and direct wordmark.
    # The final alpha mask keeps the rounded corners fully transparent.
    body = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    body_px = body.load()
    if variant == 4:
        c1 = (21, 34, 74)
        c2 = (18, 132, 140)
        c3 = (56, 72, 132)
        purple_mix = 0.22
    else:
        c1 = (38, 84, 214)
        c2 = (22, 188, 185)
        c3 = (99, 102, 241)
        purple_mix = 0.28
    for y in range(canvas):
        for x in range(canvas):
            tx = x / max(1, canvas - 1)
            ty = y / max(1, canvas - 1)
            blue_cyan = (
                _lerp(c1[0], c2[0], tx),
                _lerp(c1[1], c2[1], tx),
                _lerp(c1[2], c2[2], tx),
            )
            purple_strength = max(0.0, 1.0 - ((x - canvas * 0.18) ** 2 + (y - canvas * 0.18) ** 2) ** 0.5 / (canvas * 0.78))
            purple_strength *= purple_mix
            body_px[x, y] = (
                _lerp(blue_cyan[0], c3[0], purple_strength),
                _lerp(blue_cyan[1], c3[1], purple_strength),
                _lerp(blue_cyan[2], c3[2], purple_strength),
                255,
            )

    body_mask = Image.new("L", (canvas, canvas), 0)
    mask_draw = ImageDraw.Draw(body_mask)
    mask_draw.rounded_rectangle(
        [pad, pad, canvas - pad - 1, canvas - pad - 1],
        radius=radius,
        fill=255,
    )
    body.putalpha(body_mask)
    img.alpha_composite(body)

    accent = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    adraw = ImageDraw.Draw(accent)
    _draw_accent(adraw, canvas, variant)
    img.alpha_composite(accent)

    if variant != 4:
        glass = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glass)
        gdraw.rounded_rectangle(
            [pad * 2, pad * 2, canvas - pad * 2, int(canvas * 0.48)],
            radius=int(radius * 0.75),
            fill=(255, 255, 255, 28),
        )
        img.alpha_composite(glass)

    text = "AOMT"
    max_w = int(canvas * 0.72)
    max_h = int(canvas * 0.26)
    font, bbox = _fit_font(draw, text, max_w, max_h, int(canvas * 0.22))
    left, top, right, bottom = bbox
    text_w = right - left
    text_h = bottom - top
    x = (canvas - text_w) // 2 - left
    text_center_y = 0.66 if variant == 4 else 0.52
    y = int(canvas * text_center_y) - text_h // 2 - top

    draw = ImageDraw.Draw(img)
    text_shadow = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    shdraw = ImageDraw.Draw(text_shadow)
    shdraw.text((x, y + max(2, canvas // 90)), text, font=font, fill=(0, 30, 78, 95))
    text_shadow = text_shadow.filter(ImageFilter.GaussianBlur(radius=max(1, canvas // 120)))
    img.alpha_composite(text_shadow)
    draw = ImageDraw.Draw(img)
    draw.text((x, y), text, font=font, fill=(250, 250, 250, 255))

    if variant != 4:
        underline_w = int(canvas * 0.34)
        underline_h = max(4, int(canvas * 0.022))
        underline_x = (canvas - underline_w) // 2
        underline_y = int(canvas * 0.68)
        draw.rounded_rectangle(
            [underline_x, underline_y, underline_x + underline_w, underline_y + underline_h],
            radius=underline_h // 2,
            fill=(255, 255, 255, 210),
        )

    img.putalpha(ImageChops.multiply(img.getchannel("A"), body_mask))

    # Tiny icons cannot carry all ornamentation; downsampling keeps them crisp.
    return img.resize((size, size), Image.Resampling.LANCZOS)


def create_icon() -> None:
    try:
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        raise SystemExit("Pillow is required. Run: python -m pip install Pillow") from exc

    for variant in (1, 2, 3, 4):
        images = [_make_icon(size, variant) for size in SIZES]
        preview_path = ROOT / f"app_icon_option_{variant}.png"
        ico_path = ROOT / f"app_icon_option_{variant}.ico"
        images[-1].save(preview_path)
        images[0].save(
            ico_path,
            format="ICO",
            sizes=[(size, size) for size in SIZES],
            append_images=images[1:],
        )
        if variant == SELECTED_VARIANT:
            images[-1].save(PREVIEW_PATH)
            images[0].save(
                ICO_PATH,
                format="ICO",
                sizes=[(size, size) for size in SIZES],
                append_images=images[1:],
            )
    print(f"[OK] Icon generated: {ICO_PATH}")
    print(f"[OK] Preview generated: {PREVIEW_PATH}")
    print("[OK] Options generated: app_icon_option_1/2/3.png")


if __name__ == "__main__":
    create_icon()
