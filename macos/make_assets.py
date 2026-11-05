#!/usr/bin/env python3
"""
TEE Encryption - macOS artwork generator

Creates all images the macOS build needs from the app logo (TEE_encryption_GOLD.png):

  icon.png                1024x1024  App icon (Dock, Finder, Launchpad, Cmd+Tab).
                                     The golden lock sits on Apple's icon grid
                                     (artwork fits an 824x824 box) with the soft
                                     drop shadow of the macOS icon template, so it
                                     has the same visual size as other Dock icons.
  dmg_background.png       660x428   Background of the DMG window (arrow + hint)
  dmg_background@2x.png   1320x856   Retina version of the DMG background
  installer_logo.png       200x200   Logo shown in the .pkg installer window

Usage:
  python3 make_assets.py <logo.png> <output-dir> [--version 4.2.1]
"""

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------
# App icon (Apple macOS icon grid)
# ---------------------------------------------------------
ICON_CANVAS = 1024
ICON_BOX = 824            # artwork area of the 1024px macOS icon template
SHADOW_OFFSET = 12        # px downwards (at 1024px)
SHADOW_BLUR = 14
SHADOW_OPACITY = 0.32

# ---------------------------------------------------------
# DMG window layout (points). Keep in sync with build_macos.sh
# (DMG_WINDOW_* / DMG_*_POS variables in the Finder AppleScript).
# ---------------------------------------------------------
DMG_W, DMG_H = 660, 428   # 400pt content + 28pt reserve (Finder may count the title bar)
APP_ICON_CENTER = (165, 190)
APPS_ICON_CENTER = (495, 190)
DMG_ICON_SIZE = 128

INSTALLER_LOGO = 200


def load_logo(path):
    """Loads the logo and crops away the transparent border."""
    logo = Image.open(path).convert("RGBA")
    bbox = logo.getchannel("A").getbbox()
    if bbox:
        logo = logo.crop(bbox)
    return logo


def fit_into(img, box_w, box_h):
    """Scales an image proportionally so that it fits into box_w x box_h."""
    scale = min(box_w / img.width, box_h / img.height)
    size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    return img.resize(size, Image.LANCZOS)


def drop_shadow(art, canvas_size, pos, offset, blur, opacity):
    """Returns a transparent layer with a soft black shadow of `art` at `pos`."""
    alpha = art.getchannel("A").point(lambda a: int(a * opacity))
    shadow = Image.new("RGBA", art.size, (0, 0, 0, 0))
    shadow.putalpha(alpha)
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    layer.paste(shadow, (pos[0], pos[1] + offset))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def make_icon(logo, out_path):
    art = fit_into(logo, ICON_BOX, ICON_BOX)
    canvas = Image.new("RGBA", (ICON_CANVAS, ICON_CANVAS), (0, 0, 0, 0))
    pos = ((ICON_CANVAS - art.width) // 2, (ICON_CANVAS - art.height) // 2)
    canvas = Image.alpha_composite(
        canvas, drop_shadow(art, canvas.size, pos, SHADOW_OFFSET, SHADOW_BLUR, SHADOW_OPACITY)
    )
    canvas.alpha_composite(art, pos)
    canvas.save(out_path, optimize=True)
    return canvas


def load_font(size, bold=False):
    """System font (macOS first), falls back to Pillow's built-in font."""
    candidates = [
        ("/System/Library/Fonts/Helvetica.ttc", 1 if bold else 0),
        ("/System/Library/Fonts/HelveticaNeue.ttc", 1 if bold else 0),
        ("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
         else "/System/Library/Fonts/Supplemental/Arial.ttf", 0),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
         else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0),
    ]
    for path, index in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=index)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def centered_text(draw, center_x, y, text, font, fill, shadow=None, scale=1):
    w = draw.textlength(text, font=font)
    x = center_x - w / 2
    if shadow:
        draw.text((x, y + scale), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def make_dmg_background(out_path, scale, version):
    """
    Mid-tone slate background: Finder draws the icon labels black in light mode and
    white in dark mode - both stay readable on this background.
    """
    w, h = DMG_W * scale, DMG_H * scale
    top, bottom = (0x8F, 0x98, 0xA4), (0x6B, 0x74, 0x80)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for yy in range(h):
        t = yy / max(1, h - 1)
        row = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for xx in range(w):
            px[xx, yy] = row
    img = img.convert("RGBA")

    # subtle light "stage" behind both icons
    stage = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stage)
    pad_x, pad_top, pad_bottom = 95 * scale, 92 * scale, 300 * scale
    sd.rounded_rectangle(
        (pad_x - 40 * scale, pad_top, w - pad_x + 40 * scale, pad_bottom),
        radius=28 * scale, fill=(255, 255, 255, 34),
    )
    img = Image.alpha_composite(img, stage)

    draw = ImageDraw.Draw(img)

    # arrow from the app icon to the Applications folder
    gold = (0xF5, 0xC8, 0x42, 255)
    shadow = (0, 0, 0, 70)
    y = APP_ICON_CENTER[1] * scale
    x1 = (APP_ICON_CENTER[0] + DMG_ICON_SIZE // 2 + 22) * scale
    x2 = (APPS_ICON_CENTER[0] - DMG_ICON_SIZE // 2 - 22) * scale
    thickness = 9 * scale
    head_len, head_half = 26 * scale, 19 * scale

    def draw_arrow(color, dy):
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ad = ImageDraw.Draw(layer)
        ad.rounded_rectangle(
            (x1, y + dy - thickness // 2, x2 - head_len + 2 * scale, y + dy + thickness // 2),
            radius=thickness // 2, fill=color,
        )
        ad.polygon(
            [(x2, y + dy), (x2 - head_len, y + dy - head_half), (x2 - head_len, y + dy + head_half)],
            fill=color,
        )
        return layer

    # soft shadow first, then the crisp golden arrow on top
    img = Image.alpha_composite(img, draw_arrow(shadow, 3 * scale).filter(ImageFilter.GaussianBlur(2 * scale)))
    img = Image.alpha_composite(img, draw_arrow(gold, 0))
    draw = ImageDraw.Draw(img)

    # texts
    white = (255, 255, 255, 255)
    text_shadow = (0, 0, 0, 90)
    centered_text(draw, w / 2, 26 * scale, "Drag TEE Encryption to Applications",
                  load_font(20 * scale, bold=True), white, text_shadow, scale)
    centered_text(draw, w / 2, 56 * scale, "Zum Installieren in den Ordner „Programme“ ziehen",
                  load_font(14 * scale), (240, 242, 245, 255), text_shadow, scale)
    centered_text(draw, w / 2, 362 * scale,
                  f"TEE Encryption V{version}  ·  AES-256-GCM  ·  github.com/TheErsysEnding",
                  load_font(11 * scale), (230, 233, 238, 220), None, scale)

    img = img.convert("RGB")
    dpi = 72 * scale
    img.save(out_path, dpi=(dpi, dpi), optimize=True)


def make_installer_logo(icon_img, out_path):
    logo = icon_img.resize((INSTALLER_LOGO, INSTALLER_LOGO), Image.LANCZOS)
    logo.save(out_path, optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("logo", help="Path to TEE_encryption_GOLD.png")
    parser.add_argument("out_dir", help="Output directory")
    parser.add_argument("--version", default="4.2.1", help="Version shown on the DMG background")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    logo = load_logo(args.logo)
    if logo.width < 512 or logo.height < 512:
        print(f"[WARNUNG] Logo ist nur {logo.width}x{logo.height}px - fuer scharfe Icons "
              "werden mindestens 1024px empfohlen.", file=sys.stderr)

    icon = make_icon(logo, os.path.join(args.out_dir, "icon.png"))
    make_dmg_background(os.path.join(args.out_dir, "dmg_background.png"), 1, args.version)
    make_dmg_background(os.path.join(args.out_dir, "dmg_background@2x.png"), 2, args.version)
    make_installer_logo(icon, os.path.join(args.out_dir, "installer_logo.png"))

    for name in ("icon.png", "dmg_background.png", "dmg_background@2x.png", "installer_logo.png"):
        p = os.path.join(args.out_dir, name)
        with Image.open(p) as im:
            print(f"  {name:24s} {im.size[0]}x{im.size[1]}  {os.path.getsize(p) // 1024} KB")


if __name__ == "__main__":
    main()
