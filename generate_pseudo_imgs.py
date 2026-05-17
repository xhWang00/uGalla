import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageDraw
import piexif


RATIOS = {
    "16x9": (16, 9),
    "3x2": (3, 2),
    "1x1": (1, 1),
    "4x3": (4, 3),
}

TARGET_MP = 20_000_000
NUM_IMAGES = 25
OUTPUT = Path("static/imgs")

CAMERAS = [
    ("Canon", "EOS R5"),
    ("Canon", "EOS 5D Mark IV"),
    ("Nikon", "Z8"),
    ("Nikon", "D850"),
    ("Sony", "Alpha 7R V"),
    ("Fujifilm", "X-T5"),
    ("Leica", "M11"),
    ("Hasselblad", "X2D 100C"),
]

APERTURES = [1.4, 1.8, 2.0, 2.8, 4.0, 5.6, 8.0, 11.0, 16.0]
SHUTTER_SPEEDS = [1/8000, 1/4000, 1/2000, 1/1000, 1/500, 1/250, 1/125, 1/60, 1/30, 1/15, 1/8, 1/4, 1/2, 1]
ISOS = [100, 200, 400, 800, 1600, 3200, 6400]
FOCAL_LENGTHS = [14, 16, 24, 28, 35, 50, 85, 105, 135, 200, 400]

LOCATIONS = [
    (48.8566, 2.3522, "Paris", "France"),
    (40.4168, -3.7038, "Madrid", "Spain"),
    (35.6762, 139.6503, "Tokyo", "Japan"),
    (51.5074, -0.1278, "London", "UK"),
    (40.7128, -74.0060, "New York", "USA"),
    (37.7749, -122.4194, "San Francisco", "USA"),
    (-33.8688, 151.2093, "Sydney", "Australia"),
    (55.7558, 37.6173, "Moscow", "Russia"),
    (25.0340, 121.5645, "Taipei", "Taiwan"),
    (41.9028, 12.4964, "Rome", "Italy"),
    (52.5200, 13.4050, "Berlin", "Germany"),
    (19.0760, 72.8777, "Mumbai", "India"),
    (-23.5505, -46.6333, "São Paulo", "Brazil"),
    (31.2304, 121.4737, "Shanghai", "China"),
    (1.3521, 103.8198, "Singapore", "Singapore"),
    (34.0522, -118.2437, "Los Angeles", "USA"),
    (41.8902, 12.4922, "Vatican City", "Vatican City"),
    (27.1751, 78.0421, "Agra", "India"),
    (-22.9519, -43.2105, "Rio de Janeiro", "Brazil"),
    (35.3606, 138.7274, "Fuji", "Japan"),
]


def dimensions(ratio: tuple[int, int]) -> tuple[int, int]:
    w, h = ratio
    scale = math.sqrt(TARGET_MP / (w * h))
    return round(w * scale), round(h * scale)


def random_color() -> tuple[int, int, int]:
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


def to_exif_rational(value: float) -> tuple[int, int]:
    denom = 1000000
    return (int(round(value * denom)), denom)


def to_dms(coord: float) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    sign = -1 if coord < 0 else 1
    coord = abs(coord)
    deg = int(coord)
    min_f = (coord - deg) * 60
    sec_f = (min_f - int(min_f)) * 60
    return (
        (deg, 1),
        (int(min_f), 1),
        (int(round(sec_f * 100)), 100),
    )


def make_exif(rng: random.Random, seed: int) -> bytes:
    camera_make, camera_model = CAMERAS[seed % len(CAMERAS)]
    aperture = rng.choice(APERTURES)
    shutter_speed = rng.choice(SHUTTER_SPEEDS)
    iso = rng.choice(ISOS)
    focal_length = rng.choice(FOCAL_LENGTHS)
    lat, lon, city, country = LOCATIONS[seed % len(LOCATIONS)]

    base_date = datetime(2020, 1, 1)
    random_date = base_date + timedelta(days=rng.randint(0, 2000))
    date_str = random_date.strftime("%Y:%m:%d %H:%M:%S")

    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: camera_make,
            piexif.ImageIFD.Model: camera_model,
            piexif.ImageIFD.Software: "AI Image Generator v1.0",
            piexif.ImageIFD.Artist: f"Photographer {seed + 1:03d}",
            piexif.ImageIFD.DateTime: date_str,
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: date_str,
            piexif.ExifIFD.DateTimeDigitized: date_str,
            piexif.ExifIFD.ISOSpeedRatings: iso,
            piexif.ExifIFD.FNumber: to_exif_rational(aperture),
            piexif.ExifIFD.ExposureTime: to_exif_rational(shutter_speed),
            piexif.ExifIFD.FocalLength: to_exif_rational(focal_length),
            piexif.ExifIFD.LensModel: f"{camera_make} {focal_length}mm f/{aperture}",
        },
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: "N" if lat >= 0 else "S",
            piexif.GPSIFD.GPSLatitude: to_dms(lat),
            piexif.GPSIFD.GPSLongitudeRef: "E" if lon >= 0 else "W",
            piexif.GPSIFD.GPSLongitude: to_dms(lon),
            piexif.GPSIFD.GPSAltitudeRef: 0,
            piexif.GPSIFD.GPSAltitude: to_exif_rational(rng.uniform(10, 500)),
        },
    }

    return piexif.dump(exif_dict)


def make_image(width: int, height: int, seed: int) -> Image.Image:
    rng = random.Random(seed)
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    c1 = random_color()
    c2 = random_color()
    for y in range(height):
        t = y / height
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    for _ in range(rng.randint(50, 200)):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        r = rng.randint(10, min(width, height) // 20)
        draw.ellipse(
            [x - r, y - r, x + r, y + r],
            fill=random_color(),
            outline=None,
        )

    return img


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    existing = set(OUTPUT.iterdir())
    for i in range(NUM_IMAGES):
        name, (w_ratio, h_ratio) = list(RATIOS.items())[i % len(RATIOS)]
        w, h = dimensions((w_ratio, h_ratio))
        actual_mp = (w * h) / 1_000_000
        filename = f"img_{i:02d}_{name}_{w}x{h}.jpg"
        filepath = OUTPUT / filename
        if filepath in existing:
            print(f"Skipping {filename} (already exists)")
            continue
        img = make_image(w, h, seed=i)
        exif_bytes = make_exif(random.Random(i), i)
        img.save(filepath, quality=85, optimize=True, exif=exif_bytes)
        print(f"Created {filename}  ({actual_mp:.1f}MP, {w}x{h})")


if __name__ == "__main__":
    main()
