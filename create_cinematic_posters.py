import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cineverse.settings')
django.setup()

from PIL import Image, ImageDraw, ImageFont
from movies.models import Movie

POSTER_DIR = os.path.join('media', 'movies', 'posters')
os.makedirs(POSTER_DIR, exist_ok=True)

# Movie palette definitions
MOVIE_STYLES = {
    'Dune: Part Two': {
        'top_color': (24, 18, 12),
        'bottom_color': (180, 83, 9),
        'accent': (245, 158, 11),
        'subtitle': 'A DENIS VILLENEUVE FILM',
        'tagline': 'LONG LIVE THE FIGHTERS',
    },
    'Oppenheimer': {
        'top_color': (15, 23, 42),
        'bottom_color': (185, 28, 28),
        'accent': (251, 146, 60),
        'subtitle': 'A CHRISTOPHER NOLAN FILM',
        'tagline': 'THE WORLD FOREVER CHANGES',
    },
    'Inception': {
        'top_color': (2, 6, 23),
        'bottom_color': (30, 58, 138),
        'accent': (56, 189, 248),
        'subtitle': 'YOUR MIND IS THE SCENE OF THE CRIME',
        'tagline': 'DREAM WITHIN A DREAM',
    },
    'Gladiator II': {
        'top_color': (20, 10, 10),
        'bottom_color': (120, 20, 20),
        'accent': (245, 158, 11),
        'subtitle': 'RETURN TO THE COLOSSEUM',
        'tagline': 'WHAT WE DO IN LIFE ECHOES IN ETERNITY',
    },
    'Kalki 2898 AD': {
        'top_color': (10, 15, 30),
        'bottom_color': (88, 28, 135),
        'accent': (216, 180, 254),
        'subtitle': 'THE FUTURE BEGINS',
        'tagline': 'AN EPIC DYSTOPIAN SAGA',
    },
    'Avatar: Fire and Ash': {
        'top_color': (6, 78, 59),
        'bottom_color': (180, 83, 9),
        'accent': (52, 211, 153),
        'subtitle': 'A JAMES CAMERON FILM',
        'tagline': 'EXPLORE THE ASH TRIBE OF PANDORA',
    },
}

def create_poster(title, style, output_path):
    w, h = 600, 900
    img = Image.new('RGB', (w, h), color=style['top_color'])
    draw = ImageDraw.Draw(img)

    # Vertical Gradient
    r1, g1, b1 = style['top_color']
    r2, g2, b2 = style['bottom_color']
    for y in range(h):
        ratio = y / h
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Decorative geometric cinematic elements
    draw.rectangle([30, 30, w - 30, h - 30], outline=(255, 255, 255, 40), width=2)
    draw.rectangle([45, 45, w - 45, h - 45], outline=style['accent'], width=1)

    # Ambient glow circle
    cx, cy = w // 2, h // 2 - 40
    for rad in range(160, 40, -10):
        alpha_fill = style['accent']
        draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=alpha_fill, width=1)

    # Top Cinema branding
    draw.text((w // 2, 70), "★ CINEVERSE EXCLUSIVE PRESENTATION ★", fill=(200, 200, 200), anchor="mm")
    draw.text((w // 2, 110), style['subtitle'], fill=style['accent'], anchor="mm")

    # Center Title
    draw.text((w // 2, cy - 20), title.upper(), fill=(255, 255, 255), anchor="mm")
    draw.line([(cx - 120, cy + 20), (cx + 120, cy + 20)], fill=style['accent'], width=2)

    # Tagline
    draw.text((w // 2, cy + 50), style['tagline'], fill=(230, 230, 230), anchor="mm")

    # Bottom Cinema Formats
    draw.rectangle([60, h - 130, w - 60, h - 70], fill=(10, 15, 25))
    draw.rectangle([60, h - 130, w - 60, h - 70], outline=style['accent'], width=1)
    draw.text((w // 2, h - 100), "EXPERIENCE IN IMAX 3D • DOLBY ATMOS 4K", fill=(255, 255, 255), anchor="mm")

    img.save(output_path, quality=92)
    print(f"Generated poster for {title} at {output_path}")

for title, style in MOVIE_STYLES.items():
    movie = Movie.objects.filter(title=title).first()
    if movie:
        filename = f"{movie.slug}_poster.jpg"
        filepath = os.path.join(POSTER_DIR, filename)
        create_poster(title, style, filepath)
        movie.poster_image = f"movies/posters/{filename}"
        movie.banner_image = f"movies/posters/{filename}"
        movie.save(update_fields=['poster_image', 'banner_image'])

print("All movie posters generated and saved successfully!")
