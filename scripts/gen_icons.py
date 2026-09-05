#!/usr/bin/env python3
"""Derive favicon/OG assets for unclelyh.me from avatar.png + brand tokens."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "img")
os.makedirs(IMG, exist_ok=True)

AVATAR = os.path.join(IMG, "avatar.png")
GREEN = (47, 220, 110)        # --accent #2fdc6e
GREEN_INK = (75, 229, 132)    # --accent-ink #4be584
BG = (14, 14, 16)             # #0e0e10
FG = (233, 239, 233)          # --fg #e9efe9

avatar = Image.open(AVATAR).convert("RGB")
print("avatar source:", avatar.size)

# --- 1. PNG icons from avatar -------------------------------------------
for size, name in [(192, "icon-192.png"), (512, "icon-512.png"),
                   (180, "apple-touch-icon.png"), (32, "favicon-32.png")]:
    avatar.resize((size, size), Image.LANCZOS).save(os.path.join(IMG, name), "PNG")
    print("wrote", name, size)

# --- 2. favicon.ico (16/32/48) from avatar ------------------------------
ico_base = avatar.resize((48, 48), Image.LANCZOS)
ico_path = os.path.join(ROOT, "favicon.ico")
ico_base.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
print("wrote favicon.ico")

# --- 3. SVG monogram ------------------------------------------------------
svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <rect width="128" height="128" rx="24" fill="#0e0e10"/>
  <rect x="6" y="6" width="116" height="116" rx="20" fill="none" stroke="#232823" stroke-width="2"/>
  <text x="64" y="86" font-family="'Archivo','Helvetica Neue',Helvetica,sans-serif"
        font-size="58" font-weight="900" letter-spacing="-2" fill="#2fdc6e"
        text-anchor="middle">LYH</text>
</svg>
"""
with open(os.path.join(ROOT, "icon.svg"), "w") as f:
    f.write(svg)
print("wrote icon.svg")

# --- 4. OG image 1200x630 ------------------------------------------------
W, H = 1200, 630
og = Image.new("RGB", (W, H), BG)

# faint green ambient glow top-left like the hero's .glow
glow = Image.new("RGB", (W, H), BG)
gd = ImageDraw.Draw(glow)
gd.ellipse((-300, -250, 700, 400), fill=(20, 40, 27))
gd.ellipse((700, 350, 1500, 950), fill=(17, 30, 21))
og = Image.composite(glow, og, glow.convert("L").point(lambda p: 255 if p > BG[0] else 0))
og.paste(glow, (0, 0))
# blend the glow softly over bg
mask = Image.new("L", (W, H), 0)
md = ImageDraw.Draw(mask)
md.ellipse((-350, -300, 750, 450), fill=70)
md.ellipse((600, 350, 1550, 1000), fill=45)
mask = mask.filter(ImageFilter.GaussianBlur(120))
og = Image.composite(glow, Image.new("RGB", (W, H), BG), mask)

draw = ImageDraw.Draw(og)

def load_font(size, stretch=False):
    """Try variable Archivo (weight 900 via set_variation), fall back."""
    try:
        f = ImageFont.truetype(os.path.join(ROOT, "assets/fonts/archivo-var.woff2"), size)
        return f
    except Exception:
        pass
    for cand in ["/System/Library/Fonts/Supplemental/Impact.ttf",
                 "/System/Library/Fonts/Helvetica.ttc",
                 "/System/Library/Fonts/HelveticaNeue.ttc"]:
        if os.path.exists(cand):
            try:
                return ImageFont.truetype(cand, size)
            except Exception:
                continue
    return ImageFont.load_default(size)

# Archivo variable font: PIL supports woff2 only if compiled with it; try ttf first
font_path_ttf = None
for cand in ["/System/Library/Fonts/Supplemental/Impact.ttf",
             "/System/Library/Fonts/Helvetica.ttc",
             "/System/Library/Fonts/HelveticaNeue.ttc"]:
    if os.path.exists(cand):
        font_path_ttf = cand
        break
print("display font:", font_path_ttf)

try:
    import fontTools
    from fontTools.varLib.instancer import instantiateVariableFont
    from fontTools.ttLib import TTFont
    tt = TTFont(os.path.join(ROOT, "assets/fonts/archivo-var.woff2"))
    for axis in tt["fvar"].axes:
        if axis.axisTag == "wght":
            axis.defaultValue = 900
        if axis.axisTag == "wdth":
            axis.defaultValue = 125
    tt.flavor = None
    tmp = "/tmp/archivo-black-wide.ttf"
    instantiateVariableFont(tt, {"wght": 900, "wdth": 125}, inplace=True)
    tt.save(tmp)
    font_path_ttf = tmp
    print("instanced Archivo wght=900 wdth=125 ->", tmp)
except Exception as e:
    print("fontTools instancing failed:", e)

mono_font_path = None
for cand in ["/System/Library/Fonts/Menlo.ttc",
             "/System/Library/Fonts/Monaco.dfont",
             "/System/Library/Fonts/SFNSMono.ttf"]:
    if os.path.exists(cand):
        mono_font_path = cand
        break
print("mono font:", mono_font_path)

# Hero mirrors index.html: eyebrow (mono, uppercase), stacked wordmark, .me green
f_eyebrow = ImageFont.truetype(mono_font_path, 24)
f_name = ImageFont.truetype(font_path_ttf, 220)
f_tld = ImageFont.truetype(mono_font_path, 54)
f_tag = ImageFont.truetype(mono_font_path, 20)

draw = ImageDraw.Draw(og)

def center_text(y, text, font, fill, glow_color=None, glow_passes=0):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2 - bbox[0]
    if glow_color and glow_passes:
        for i in range(glow_passes, 0, -1):
            gmask = Image.new("L", (W, H), 0)
            ImageDraw.Draw(gmask).text((x, y), text, font=font, fill=255)
            gmask = gmask.filter(ImageFilter.GaussianBlur(6 * i))
            tinted = Image.new("RGB", (W, H), glow_color)
            og.paste(tinted, (0, 0), gmask.point(lambda p, k=i: int(p * (0.18 / k))))
    draw.text((x, y), text, font=font, fill=fill)

# eyebrow row like hero-eyebrow
center_text(72, "DEVELOPER & PLATFORM ENGINEER", f_eyebrow, (101, 110, 101))
# stacked wordmark like hero: row1 solid, row2 outline-ish
center_text(150, "UNCLE", f_name, FG, glow_color=(47, 220, 110), glow_passes=2)
center_text(370, "LYHME", f_name, GREEN, glow_color=(47, 220, 110), glow_passes=3)
# tagline row with .me green like wordmark .tld — one line, one baseline
draw = ImageDraw.Draw(og)
base = "unclelyh"
me = ".me"
bb = draw.textbbox((0, 0), base, font=f_tag)
mb = draw.textbbox((0, 0), me, font=f_tag)
gap = 2
total = (bb[2] - bb[0]) + gap + (mb[2] - mb[0])
x0 = (W - total) // 2
ty = 585
draw.text((x0 - bb[0], ty), base, font=f_tag, fill=(159, 168, 159))
draw.text((x0 + (bb[2] - bb[0]) + gap - mb[0], ty), me, font=f_tag, fill=GREEN_INK)

og.save(os.path.join(IMG, "og-image.png"), "PNG")
print("wrote og-image.png", og.size)
