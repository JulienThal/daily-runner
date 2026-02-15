import io
import os
import sys
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Dimensions principales
WIDTH, HEIGHT = 1080, 1920

SAFE_TOP = 250
SAFE_BOTTOM = 350
SAFE_RIGHT = 200

# Gestion des chemins (PyInstaller + exécution normale)
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Chemins des polices
FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")
FONT_BOLD_PATH = os.path.join(FONTS_DIR, "Roboto-Bold.ttf")
FONT_REGULAR_PATH = os.path.join(FONTS_DIR, "Roboto-Regular.ttf")

# -------------------------------------------------------------------
# Helpers typographiques
# -------------------------------------------------------------------
def load_font(path, size, fallback=None):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return fallback or ImageFont.load_default()

def measure(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def wrap_lines(draw, text, font, max_width, max_lines=3):
    words = text.split()
    lines = []
    current = ""

    for w in words:
        test = (current + " " + w).strip()
        tw, _ = measure(draw, test, font)
        if tw <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
            if len(lines) == max_lines - 1:
                break

    if current:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines-1] + [" ".join(lines[max_lines-1:])]

    return lines

# -------------------------------------------------------------------
# Gestion des logos (cache + fallback)
# -------------------------------------------------------------------
_logo_cache = {}

def load_logo(url, size=(80, 80)):
    if not url:
        return Image.new("RGBA", size, (60, 60, 60, 255))

    if url in _logo_cache:
        return _logo_cache[url]

    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        img.thumbnail(size, Image.LANCZOS)
    except Exception:
        img = Image.new("RGBA", size, (60, 60, 60, 255))

    _logo_cache[url] = img
    return img

# -------------------------------------------------------------------
# Génération d'image (version cloud : retourne des bytes)
# -------------------------------------------------------------------
def generate_image(resultat: dict, date_str):
    margin_x = 40
    block_radius = 24
    block_padding_top = 48
    block_padding_bottom = 30
    logo_size_comp = (60, 60)
    team_logo_nominal = (48, 48)
    team_logo_x = margin_x + 40

    block_right = WIDTH - SAFE_RIGHT
    score_right_margin = 40
    score_x = block_right - score_right_margin

    text_max_width = block_right - (team_logo_x + team_logo_nominal[0] + 24 + score_right_margin + 20)

    line_spacing = 30
    inter_team_gap = 8
    match_vertical_padding = 20
    league_spacing = 36

    # Polices
    font_title = load_font(FONT_BOLD_PATH, 60)
    font_league = load_font(FONT_BOLD_PATH, 46, fallback=font_title)
    font_team = load_font(FONT_REGULAR_PATH, 36)
    font_score = load_font(FONT_BOLD_PATH, 44, fallback=font_title)

    # ---------------------------------------------------------
    # Nouvelle page
    # ---------------------------------------------------------
    def new_canvas(page_num):
        img = Image.new("RGB", (WIDTH, HEIGHT), (241, 245, 249))
        draw = ImageDraw.Draw(img)

        usable_width = WIDTH - SAFE_RIGHT
        title_text = f"Résultats du {date_str}"
        font_size = 60

        while True:
            font_title_dyn = load_font(FONT_BOLD_PATH, font_size, fallback=font_title)
            tw, th = measure(draw, title_text, font_title_dyn)
            if tw <= usable_width - margin_x - 20 or font_size <= 32:
                break
            font_size -= 4

        draw.text((margin_x, SAFE_TOP), title_text, fill="black", font=font_title_dyn)
        return img, draw, th, font_title_dyn

    # ---------------------------------------------------------
    # Début
    # ---------------------------------------------------------
    page = 1
    img, draw, title_h, font_title_dyn = new_canvas(page)
    y = SAFE_TOP + title_h + 40

    images_bytes = []

    # ---------------------------------------------------------
    # Parcours des ligues
    # ---------------------------------------------------------
    for league_code, league_data in resultat.items():

        matches = league_data.get("matches", [])
        if not matches:
            continue

        league_display_name = league_data.get("name") or league_code

        MAX_MATCHES_PER_BLOCK = 6
        match_chunks = [
            matches[i:i + MAX_MATCHES_PER_BLOCK]
            for i in range(0, len(matches), MAX_MATCHES_PER_BLOCK)
        ]

        # ---------------------------------------------------------
        # Parcours des chunks
        # ---------------------------------------------------------
        for chunk in match_chunks:

            header_height = 60
            total_height = block_padding_top + header_height
            match_infos = []

            # Pré-calcul des hauteurs
            for match in chunk:
                home = match["homeTeam"]["name"]
                away = match["awayTeam"]["name"]

                home_lines = wrap_lines(draw, home, font_team, text_max_width)
                away_lines = wrap_lines(draw, away, font_team, text_max_width)

                line_h = measure(draw, "Ay", font_team)[1]
                home_h = len(home_lines) * (line_h + line_spacing)
                away_h = len(away_lines) * (line_h + line_spacing)

                content_h = home_h + inter_team_gap + away_h
                min_content_h = max(content_h, team_logo_nominal[1] * 2)
                match_h = min_content_h + 2 * match_vertical_padding

                match_infos.append({
                    "match": match,
                    "home_lines": home_lines,
                    "away_lines": away_lines,
                    "height": match_h,
                    "home_h": home_h,
                    "away_h": away_h,
                    "line_h": line_h
                })

                total_height += match_h

            total_height += block_padding_bottom

            # Nouvelle page si dépassement
            if y + total_height > HEIGHT - SAFE_BOTTOM:
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                buffer.seek(0)
                images_bytes.append(buffer.getvalue())

                page += 1
                img, draw, title_h, font_title_dyn = new_canvas(page)
                y = SAFE_TOP + title_h + 40

            # ---------------------------------------------------------
            # Bloc ligue
            # ---------------------------------------------------------
            top = y
            bottom = y + total_height

            draw.rounded_rectangle(
                (margin_x, top, block_right, bottom),
                radius=block_radius,
                fill=(19, 39, 97)
            )

            league_logo_url = league_data.get("competition", {}).get("emblem")
            league_logo = load_logo(league_logo_url, size=logo_size_comp) if league_logo_url else None

            lx = margin_x + 24
            ly = top + 18

            if league_logo:
                img.paste(league_logo, (lx, ly), league_logo)
                lx += logo_size_comp[0] + 12

            draw.text((lx, ly + 8), league_display_name, fill="white", font=font_league)

            cursor_y = top + block_padding_top + header_height

            # ---------------------------------------------------------
            # Matches du chunk
            # ---------------------------------------------------------
            for info in match_infos:
                match = info["match"]
                match_h = info["height"]
                row_top = cursor_y
                content_area_h = match_h - 2 * match_vertical_padding
                half_h = content_area_h // 2

                home_logo = load_logo(match["homeTeam"].get("crest"), size=team_logo_nominal)
                away_logo = load_logo(match["awayTeam"].get("crest"), size=team_logo_nominal)

                max_logo_h = min(team_logo_nominal[1], half_h)
                if max_logo_h < team_logo_nominal[1]:
                    scale = max_logo_h / team_logo_nominal[1]
                    new_w = max(8, int(team_logo_nominal[0] * scale))
                    home_logo = home_logo.copy().resize((new_w, max_logo_h), Image.LANCZOS)
                    away_logo = away_logo.copy().resize((new_w, max_logo_h), Image.LANCZOS)

                line_h = info["line_h"]
                full = match["score"]["fullTime"]

                score_home = "-" if full["home"] is None else str(full["home"])
                score_away = "-" if full["away"] is None else str(full["away"])

                # HOME
                sw_home, sh_home = measure(draw, score_home, font_score)
                home_text_total_h = len(info["home_lines"]) * (line_h + line_spacing) - line_spacing
                home_row_h = max(home_logo.size[1], home_text_total_h, sh_home)

                home_center_y = row_top + match_vertical_padding + (half_h - home_row_h) // 2
                home_logo_y = home_center_y + (home_row_h - home_logo.size[1]) // 2

                img.paste(home_logo, (team_logo_x, int(home_logo_y)), home_logo)

                text_x = team_logo_x + max(home_logo.size[0], away_logo.size[0]) + 16
                ty = home_center_y + (home_row_h - home_text_total_h) // 2

                for line in info["home_lines"]:
                    draw.text((text_x, ty), line, fill="white", font=font_team)
                    ty += line_h + line_spacing

                score_y = home_center_y + (home_row_h - sh_home) // 2

                # 🔧 Correction ici
                draw.text((score_x - sw_home, score_y), score_home, fill=(33, 188, 255), font=font_score)

                # AWAY
                sw_away, sh_away = measure(draw, score_away, font_score)
                away_text_total_h = len(info["away_lines"]) * (line_h + line_spacing) - line_spacing
                away_row_h = max(away_logo.size[1], away_text_total_h, sh_away)

                away_center_y = row_top + match_vertical_padding + half_h + (half_h - away_row_h) // 2
                away_logo_y = away_center_y + (away_row_h - away_logo.size[1]) // 2

                img.paste(away_logo, (team_logo_x, int(away_logo_y)), away_logo)

                ty = away_center_y + (away_row_h - away_text_total_h) // 2
                for line in info["away_lines"]:
                    draw.text((text_x, ty), line, fill="white", font=font_team)
                    ty += line_h + line_spacing

                score_y = away_center_y + (away_row_h - sh_away) // 2

                # 🔧 Correction ici
                draw.text((score_x - sw_away, score_y), score_away, fill=(33, 188, 255), font=font_score)

                cursor_y += match_h

            y = bottom + league_spacing

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            images_bytes.append(buffer.getvalue())

            page += 1
            img, draw, title_h, font_title_dyn = new_canvas(page)
            y = SAFE_TOP + title_h + 40

    return images_bytes
