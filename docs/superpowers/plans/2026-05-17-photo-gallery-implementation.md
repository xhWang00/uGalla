# uGalla Photo Gallery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a brutalist Flask photo gallery that serves images from `static/` subfolders with pagination, masonry layout, and lightbox EXIF viewer.

**Architecture:** Flask app with startup cache — GalleryScanner walks `static/` subdirectories on init, extracts EXIF via Pillow, and caches in memory. Routes paginate from cache (10/page). Lightbox fetches EXIF from a JSON API endpoint.

**Tech Stack:** Python 3.10+, Flask 3.x, Jinja2, Pillow, JetBrains Mono (Google Fonts)

---

### Task 1: Project setup and dependencies

**Files:**
- Create: `requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Write requirements.txt**

```
Flask>=3.0
Pillow>=10.0
```

- [ ] **Step 2: Update .gitignore to exclude assets symlink/cache**

Replace current content (`static/*`) with:

```
static/imgs/*
```

This way the `static/assets/` directory (CSS, JS) is tracked by git, while images remain ignored.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt .gitignore
git commit -m "chore: project dependencies and gitignore"
```

---

### Task 2: Implement GalleryScanner

**Files:**
- Create: `gallery.py`

- [ ] **Step 1: Write gallery.py with ImageMeta dataclass and GalleryScanner**

```python
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image, ExifTags


@dataclass
class ImageMeta:
    gallery: str
    filename: str
    path: str
    width: int
    height: int
    date_taken: Optional[str] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    focal_length: Optional[str] = None
    aperture: Optional[str] = None
    shutter: Optional[str] = None
    iso: Optional[int] = None
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    location_city: Optional[str] = None
    location_country: Optional[str] = None


def _dms_to_decimal(dms: tuple, ref: str) -> float:
    if not dms or len(dms) < 3:
        return 0.0
    deg = float(dms[0][0]) / float(dms[0][1]) if dms[0][1] else 0
    minute = float(dms[1][0]) / float(dms[1][1]) if dms[1][1] else 0
    sec = float(dms[2][0]) / float(dms[2][1]) if dms[2][1] else 0
    decimal = deg + minute / 60.0 + sec / 3600.0
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def _rational_to_float(val) -> float:
    if isinstance(val, tuple) and len(val) == 2 and val[1] != 0:
        return round(float(val[0]) / float(val[1]), 1)
    return float(val) if val else 0.0


IMG_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tiff", ".bmp"}

EXIF_DATETIME_ORIGINAL = 36867
EXIF_MAKE = 271
EXIF_MODEL = 272
EXIF_FOCAL_LENGTH = 37386
EXIF_FNUMBER = 33437
EXIF_EXPOSURE_TIME = 33434
EXIF_ISO = 34855
GPS_INFO_TAG = 34853
GPS_LAT_TAG = 2
GPS_LON_TAG = 4
GPS_LAT_REF_TAG = 1
GPS_LON_REF_TAG = 3


def _parse_shutter(rational) -> str:
    if isinstance(rational, tuple) and len(rational) == 2:
        num, den = rational[0], rational[1]
        if den and num:
            if num > den:
                val = num / den
                return f"1/{round(1/val)}" if val < 1 else str(round(val))
            return f"{num}/{den}" if num == 1 else f"1/{round(den/num)}"
    return str(rational)


class GalleryScanner:
    def __init__(self, static_dir: str | Path = "static"):
        self.static_dir = Path(static_dir)
        self._galleries: dict[str, list[ImageMeta]] = {}
        self._gallery_order: list[str] = []
        self.scan()

    def scan(self) -> None:
        self._galleries = {}
        self._gallery_order = []
        if not self.static_dir.is_dir():
            return
        for entry in sorted(self.static_dir.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.startswith("."):
                continue
            if entry.name == "__pycache__":
                continue
            images = self._scan_gallery(entry.name)
            if images:
                self._galleries[entry.name] = images
                self._gallery_order.append(entry.name)

    def _scan_gallery(self, gallery_name: str) -> list[ImageMeta]:
        gallery_path = self.static_dir / gallery_name
        images: list[ImageMeta] = []
        for fname in sorted(gallery_path.iterdir()):
            if fname.suffix.lower() not in IMG_EXTENSIONS:
                continue
            meta = self._read_exif(gallery_name, fname)
            if meta:
                images.append(meta)
        images.sort(key=lambda m: m.date_taken or "", reverse=True)
        return images

    def _read_exif(self, gallery: str, fpath: Path) -> Optional[ImageMeta]:
        try:
            img = Image.open(fpath)
            w, h = img.size
            exif_data = img._getexif()
            if exif_data is None:
                exif_data = {}
            date_taken = None
            camera_make = None
            camera_model = None
            focal_length = None
            aperture = None
            shutter = None
            iso = None
            gps_lat = None
            gps_lon = None

            if exif_data:
                if EXIF_DATETIME_ORIGINAL in exif_data:
                    date_taken = str(exif_data[EXIF_DATETIME_ORIGINAL])
                if EXIF_MAKE in exif_data:
                    camera_make = str(exif_data[EXIF_MAKE]).strip()
                if EXIF_MODEL in exif_data:
                    camera_model = str(exif_data[EXIF_MODEL]).strip()
                if EXIF_FOCAL_LENGTH in exif_data:
                    fl = _rational_to_float(exif_data[EXIF_FOCAL_LENGTH])
                    focal_length = f"{int(fl)}mm" if fl else None
                if EXIF_FNUMBER in exif_data:
                    ap = _rational_to_float(exif_data[EXIF_FNUMBER])
                    aperture = f"f/{ap}" if ap else None
                if EXIF_EXPOSURE_TIME in exif_data:
                    shutter = _parse_shutter(exif_data[EXIF_EXPOSURE_TIME])
                if EXIF_ISO in exif_data:
                    iso = int(exif_data[EXIF_ISO])

                gps_info = exif_data.get(GPS_INFO_TAG)
                if gps_info and isinstance(gps_info, dict):
                    lat_dms = gps_info.get(GPS_LAT_TAG)
                    lat_ref = gps_info.get(GPS_LAT_REF_TAG, b"N")
                    lon_dms = gps_info.get(GPS_LON_TAG)
                    lon_ref = gps_info.get(GPS_LON_REF_TAG, b"E")
                    if lat_dms and lon_dms:
                        gps_lat = round(_dms_to_decimal(lat_dms, lat_ref.decode()), 6)
                        gps_lon = round(_dms_to_decimal(lon_dms, lon_ref.decode()), 6)

            img.close()
            return ImageMeta(
                gallery=gallery,
                filename=fpath.name,
                path=f"{gallery}/{fpath.name}",
                width=w,
                height=h,
                date_taken=date_taken,
                camera_make=camera_make,
                camera_model=camera_model,
                focal_length=focal_length,
                aperture=aperture,
                shutter=shutter,
                iso=iso,
                gps_lat=gps_lat,
                gps_lon=gps_lon,
            )
        except Exception:
            return None

    @property
    def galleries(self) -> list[str]:
        return list(self._gallery_order)

    def get_images(self, gallery: str, page: int = 1, per_page: int = 10) -> tuple[list[ImageMeta], int]:
        images = self._galleries.get(gallery, [])
        total = len(images)
        start = (page - 1) * per_page
        end = start + per_page
        return images[start:end], total

    def get_latest(self, page: int = 1, per_page: int = 10) -> tuple[list[ImageMeta], int]:
        all_images: list[ImageMeta] = []
        for g in self._gallery_order:
            all_images.extend(self._galleries[g])
        all_images.sort(key=lambda m: m.date_taken or "", reverse=True)
        total = len(all_images)
        start = (page - 1) * per_page
        end = start + per_page
        return all_images[start:end], total

    def get_exif(self, gallery: str, filename: str) -> Optional[dict]:
        images = self._galleries.get(gallery, [])
        for img in images:
            if img.filename == filename:
                return {
                    "camera": f"{img.camera_make or ''} {img.camera_model or ''}".strip(),
                    "focal_length": img.focal_length,
                    "aperture": img.aperture,
                    "shutter": img.shutter,
                    "iso": img.iso,
                    "date": img.date_taken,
                    "dimensions": f"{img.width}x{img.height}",
                    "path": img.path,
                    "filename": img.filename,
                }
        return None
```

- [ ] **Step 2: Commit**

```bash
git add gallery.py
git commit -m "feat: add GalleryScanner with EXIF extraction and caching"
```

---

### Task 3: Implement Flask app

**Files:**
- Create: `app.py`

- [ ] **Step 1: Write app.py**

```python
from __future__ import annotations

import os

from flask import Flask, Response, jsonify, render_template, request

from gallery import GalleryScanner

app = Flask(__name__)

STATIC_DIR = os.path.join(app.root_path, "static")
PER_PAGE = 10

scanner = GalleryScanner(STATIC_DIR)


@app.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    images, total = scanner.get_latest(page, PER_PAGE)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    return render_template(
        "index.html",
        images=images,
        page=page,
        total_pages=total_pages,
        galleries=scanner.galleries,
    )


@app.route("/<gallery_name>/")
def gallery(gallery_name: str):
    if gallery_name not in scanner.galleries:
        return render_template("gallery.html", images=[], page=1, total_pages=1, gallery_name=gallery_name, galleries=scanner.galleries), 404
    page = request.args.get("page", 1, type=int)
    images, total = scanner.get_images(gallery_name, page, PER_PAGE)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    return render_template(
        "gallery.html",
        images=images,
        page=page,
        total_pages=total_pages,
        gallery_name=gallery_name,
        galleries=scanner.galleries,
    )


@app.route("/api/exif/<gallery_name>/<filename>")
def api_exif(gallery_name: str, filename: str):
    data = scanner.get_exif(gallery_name, filename)
    if data is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)
```

- [ ] **Step 2: Commit**

```bash
git add app.py
git commit -m "feat: Flask app with index, gallery, and EXIF API routes"
```

---

### Task 4: Create base template

**Files:**
- Create: `templates/base.html`

- [ ] **Step 1: Write templates/base.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}uGalla{% endblock %}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{{ url_for('static', filename='assets/css/style.css') }}">
</head>
<body>
  <header class="header">
    <div class="header__inner">
      <a href="{{ url_for('index') }}" class="header__title">uGalla</a>
      <button class="header__burger" id="burger" aria-label="Menu">&#9776;</button>
      <nav class="header__nav" id="nav">
        <a href="{{ url_for('index') }}" class="header__link">All</a>
        {% for g in galleries %}
        <a href="{{ url_for('gallery', gallery_name=g) }}" class="header__link{% if gallery_name == g %} header__link--active{% endif %}">{{ g }}</a>
        {% endfor %}
      </nav>
    </div>
  </header>

  <main class="main">
    {% block content %}{% endblock %}
  </main>

  <div class="lightbox" id="lightbox">
    <button class="lightbox__close" id="lightbox-close">&times;</button>
    <button class="lightbox__prev" id="lightbox-prev">&#9664;</button>
    <img class="lightbox__image" id="lightbox-image" alt="">
    <button class="lightbox__next" id="lightbox-next">&#9654;</button>
    <div class="lightbox__info" id="lightbox-info"></div>
  </div>

  <script src="{{ url_for('static', filename='assets/js/gallery.js') }}"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/base.html
git commit -m "feat: base template with header, burger, lightbox shell"
```

---

### Task 5: Create index template

**Files:**
- Create: `templates/index.html`

- [ ] **Step 1: Write templates/index.html**

```html
{% extends "base.html" %}
{% block title %}uGalla — All{% endblock %}
{% block content %}
<div class="page-header">
  <h1 class="page-header__title">All Photos</h1>
</div>
<div class="masonry">
  {% for img in images %}
  <div class="card" data-gallery="{{ img.gallery }}" data-filename="{{ img.filename }}">
    <img class="card__image" src="{{ url_for('static', filename=img.path) }}" alt="{{ img.filename }}" loading="lazy">
    <div class="card__meta">
      <span class="card__gallery">{{ img.gallery }}</span>
      <span class="card__date">{{ img.date_taken[:10] if img.date_taken else '' }}</span>
    </div>
  </div>
  {% endfor %}
</div>
<div class="pagination">
  {% if page > 1 %}
  <a href="{{ url_for('index', page=page-1) }}" class="pagination__link">&#9664; Previous</a>
  {% endif %}
  <span class="pagination__info">Page {{ page }} of {{ total_pages }}</span>
  {% if page < total_pages %}
  <a href="{{ url_for('index', page=page+1) }}" class="pagination__link">Next &#9654;</a>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/index.html
git commit -m "feat: index template with masonry and pagination"
```

---

### Task 6: Create gallery template

**Files:**
- Create: `templates/gallery.html`

- [ ] **Step 1: Write templates/gallery.html**

```html
{% extends "base.html" %}
{% block title %}uGalla — {{ gallery_name }}{% endblock %}
{% block content %}
<div class="page-header">
  <h1 class="page-header__title">{{ gallery_name }}</h1>
</div>
{% if images %}
<div class="masonry">
  {% for img in images %}
  <div class="card" data-gallery="{{ img.gallery }}" data-filename="{{ img.filename }}">
    <img class="card__image" src="{{ url_for('static', filename=img.path) }}" alt="{{ img.filename }}" loading="lazy">
    <div class="card__meta">
      <span class="card__gallery">{{ img.gallery }}</span>
      <span class="card__date">{{ img.date_taken[:10] if img.date_taken else '' }}</span>
    </div>
  </div>
  {% endfor %}
</div>
<div class="pagination">
  {% if page > 1 %}
  <a href="{{ url_for('gallery', gallery_name=gallery_name, page=page-1) }}" class="pagination__link">&#9664; Previous</a>
  {% endif %}
  <span class="pagination__info">Page {{ page }} of {{ total_pages }}</span>
  {% if page < total_pages %}
  <a href="{{ url_for('gallery', gallery_name=gallery_name, page=page+1) }}" class="pagination__link">Next &#9654;</a>
  {% endif %}
</div>
{% else %}
<p class="empty-state">No images found in this gallery.</p>
{% endif %}
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/gallery.html
git commit -m "feat: gallery template with masonry and pagination"
```

---

### Task 7: CSS — brutalism style

**Files:**
- Create: `static/assets/css/style.css`

- [ ] **Step 1: Write style.css**

```css
*, *::before, *::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --black: #000;
  --white: #fff;
  --accent: #cc0000;
  --font: 'JetBrains Mono', 'Courier New', monospace;
  --space: 16px;
  --border: 1px solid var(--black);
}

html {
  font-size: 16px;
}

body {
  font-family: var(--font);
  color: var(--black);
  background: var(--white);
  line-height: 1.5;
  padding-top: 60px;
}

a {
  color: inherit;
  text-decoration: none;
}

a:hover {
  color: var(--accent);
}

/* Header */
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: var(--white);
  border-bottom: var(--border);
  z-index: 100;
}

.header__inner {
  display: flex;
  align-items: center;
  padding: 0 var(--space);
  height: 60px;
  max-width: 1400px;
  margin: 0 auto;
}

.header__title {
  font-weight: 700;
  font-size: 1.25rem;
  margin-right: auto;
}

.header__burger {
  display: none;
  background: none;
  border: var(--border);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 4px 10px;
  font-family: var(--font);
  color: var(--black);
}

.header__nav {
  display: flex;
  gap: var(--space);
}

.header__link {
  font-size: 0.875rem;
  text-transform: uppercase;
}

.header__link--active {
  text-decoration: underline;
  text-underline-offset: 4px;
}

.header__nav-open {
  display: flex;
}

/* Main */
.main {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space);
}

/* Page header */
.page-header {
  margin-bottom: var(--space);
  border-bottom: var(--border);
  padding-bottom: 8px;
}

.page-header__title {
  font-size: 1.5rem;
  font-weight: 700;
}

/* Masonry */
.masonry {
  column-count: 4;
  column-gap: var(--space);
}

.card {
  display: inline-block;
  width: 100%;
  border: var(--border);
  padding: 8px;
  margin-bottom: var(--space);
  break-inside: avoid;
  background: var(--white);
  cursor: pointer;
  transition: border-color 0.15s;
}

.card:hover {
  border-color: var(--accent);
}

.card__image {
  display: block;
  width: 100%;
  height: auto;
}

.card__meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  margin-top: 6px;
  text-transform: uppercase;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--space);
  padding: var(--space) 0;
  border-top: var(--border);
  margin-top: var(--space);
}

.pagination__link {
  border: var(--border);
  padding: 6px 12px;
  font-size: 0.875rem;
  font-family: var(--font);
}

.pagination__link:hover {
  background: var(--black);
  color: var(--white);
}

.pagination__info {
  font-size: 0.75rem;
}

/* Empty state */
.empty-state {
  padding: calc(var(--space) * 4) 0;
  text-align: center;
  font-size: 1rem;
}

/* Lightbox */
.lightbox {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  z-index: 200;
  align-items: center;
  justify-content: center;
}

.lightbox--open {
  display: flex;
}

.lightbox__image {
  max-width: 90vw;
  max-height: 85vh;
  object-fit: contain;
  border: 1px solid var(--white);
}

.lightbox__close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: 1px solid var(--white);
  color: var(--white);
  font-size: 1.5rem;
  cursor: pointer;
  width: 40px;
  height: 40px;
  font-family: var(--font);
}

.lightbox__prev,
.lightbox__next {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: 1px solid var(--white);
  color: var(--white);
  font-size: 1.5rem;
  cursor: pointer;
  width: 40px;
  height: 60px;
  font-family: var(--font);
}

.lightbox__prev { left: 16px; }
.lightbox__next { right: 16px; }

.lightbox__info {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--white);
  border-top: var(--border);
  padding: var(--space);
  font-size: 0.75rem;
  display: none;
  max-height: 40vh;
  overflow-y: auto;
}

.lightbox__info--open {
  display: block;
}

.lightbox__info table {
  width: 100%;
  border-collapse: collapse;
}

.lightbox__info td {
  padding: 4px 8px;
  border-bottom: 1px solid #ccc;
}

.lightbox__info td:first-child {
  font-weight: 700;
  width: 40%;
}

.lightbox__info-btn {
  position: absolute;
  bottom: 16px;
  right: 16px;
  background: var(--white);
  border: 1px solid var(--black);
  color: var(--black);
  cursor: pointer;
  font-family: var(--font);
  font-size: 0.75rem;
  padding: 4px 8px;
}

/* Responsive */
@media (max-width: 1200px) {
  .masonry { column-count: 3; }
}

@media (max-width: 768px) {
  .masonry { column-count: 2; }

  .header__burger {
    display: block;
  }

  .header__nav {
    display: none;
    position: absolute;
    top: 60px;
    left: 0;
    right: 0;
    flex-direction: column;
    background: var(--white);
    border-bottom: var(--border);
    padding: var(--space);
    gap: 8px;
  }

  .header__nav-open {
    display: flex;
  }

  .lightbox__prev,
  .lightbox__next {
    width: 32px;
    height: 48px;
    font-size: 1rem;
  }
}

@media (max-width: 480px) {
  .masonry { column-count: 1; }

  .card__meta {
    flex-direction: column;
    gap: 2px;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add static/assets/css/style.css
git commit -m "feat: brutalism CSS with masonry, header, lightbox, responsive"
```

---

### Task 8: JavaScript — lightbox and EXIF

**Files:**
- Create: `static/assets/js/gallery.js`

- [ ] **Step 1: Write gallery.js**

```javascript
(function () {
  'use strict';

  var lightbox = document.getElementById('lightbox');
  var lightboxImage = document.getElementById('lightbox-image');
  var lightboxInfo = document.getElementById('lightbox-info');
  var lightboxClose = document.getElementById('lightbox-close');
  var lightboxPrev = document.getElementById('lightbox-prev');
  var lightboxNext = document.getElementById('lightbox-next');
  var burger = document.getElementById('burger');
  var nav = document.getElementById('nav');

  var currentIndex = -1;
  var currentImages = [];

  // Burger menu toggle
  burger.addEventListener('click', function () {
    nav.classList.toggle('header__nav-open');
  });

  // Close nav on link click (mobile)
  nav.addEventListener('click', function () {
    nav.classList.remove('header__nav-open');
  });

  function buildExifTable(data) {
    var rows = '';
    var fields = [
      ['Camera', data.camera],
      ['Focal Length', data.focal_length],
      ['Aperture', data.aperture],
      ['Shutter', data.shutter],
      ['ISO', data.iso],
      ['Date', data.date],
      ['Dimensions', data.dimensions],
    ];
    for (var i = 0; i < fields.length; i++) {
      if (fields[i][1]) {
        rows += '<tr><td>' + fields[i][0] + '</td><td>' + fields[i][1] + '</td></tr>';
      }
    }
    return '<table>' + rows + '</table>';
  }

  function openLightbox(index) {
    if (index < 0 || index >= currentImages.length) return;
    currentIndex = index;
    var card = currentImages[index];
    var img = card.querySelector('.card__image');
    lightboxImage.src = img.src;
    lightboxImage.alt = img.alt;
    lightbox.classList.add('lightbox--open');
    lightboxInfo.classList.remove('lightbox__info--open');
    lightboxInfo.innerHTML = '';

    // Fetch EXIF data
    var gallery = card.getAttribute('data-gallery');
    var filename = card.getAttribute('data-filename');
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/exif/' + encodeURIComponent(gallery) + '/' + encodeURIComponent(filename), true);
    xhr.onload = function () {
      if (xhr.status === 200) {
        var data = JSON.parse(xhr.responseText);
        lightboxInfo.innerHTML = buildExifTable(data);
        lightboxInfo.classList.add('lightbox__info--open');
      }
    };
    xhr.send();
  }

  function closeLightbox() {
    lightbox.classList.remove('lightbox--open');
    lightboxInfo.classList.remove('lightbox__info--open');
    currentIndex = -1;
  }

  function prevImage() {
    openLightbox(currentIndex - 1);
  }

  function nextImage() {
    openLightbox(currentIndex + 1);
  }

  // Collect all cards
  var cards = document.querySelectorAll('.card');
  for (var i = 0; i < cards.length; i++) {
    (function (idx) {
      cards[idx].addEventListener('click', function () {
        currentImages = document.querySelectorAll('.card');
        openLightbox(idx);
      });
    })(i);
  }

  // Lightbox controls
  lightboxClose.addEventListener('click', closeLightbox);
  lightboxPrev.addEventListener('click', prevImage);
  lightboxNext.addEventListener('click', nextImage);

  document.addEventListener('keydown', function (e) {
    if (!lightbox.classList.contains('lightbox--open')) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') prevImage();
    if (e.key === 'ArrowRight') nextImage();
  });

  // Close lightbox on background click
  lightbox.addEventListener('click', function (e) {
    if (e.target === lightbox) closeLightbox();
  });
})();
```

- [ ] **Step 2: Commit**

```bash
git add static/assets/js/gallery.js
git commit -m "feat: lightbox with EXIF fetch and keyboard navigation"
```

---

### Task 9: Generate test images with multi-gallery structure

**Files:**
- Modify: `generate_pseudo_imgs.py` — output to dated subfolders
- Run: script to produce images in `static/2025-01/`, `static/2025-02/`, etc.

- [ ] **Step 1: Update generate_pseudo_imgs.py to use dated subfolders**

Replace the `OUTPUT` constant and add date-bucketed output:

```python
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
NUM_IMAGES = 60

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
    coord = abs(coord)
    deg = int(coord)
    min_f = (coord - deg) * 60
    sec_f = (min_f - int(min_f)) * 60
    return (
        (deg, 1),
        (int(min_f), 1),
        (int(round(sec_f * 100)), 100),
    )


def make_exif(rng: random.Random, seed: int, dt: datetime) -> bytes:
    camera_make, camera_model = CAMERAS[seed % len(CAMERAS)]
    aperture = rng.choice(APERTURES)
    shutter_speed = rng.choice(SHUTTER_SPEEDS)
    iso = rng.choice(ISOS)
    focal_length = rng.choice(FOCAL_LENGTHS)
    lat, lon, city, country = LOCATIONS[seed % len(LOCATIONS)]

    date_str = dt.strftime("%Y:%m:%d %H:%M:%S")

    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: camera_make,
            piexif.ImageIFD.Model: camera_model,
            piexif.ImageIFD.Software: "uGalla Generator v1.0",
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
    base = Path("static")
    base.mkdir(parents=True, exist_ok=True)

    # Create 3 monthly galleries: 2025-01, 2025-02, 2025-03
    months = ["2025-01", "2025-02", "2025-03"]
    images_per_month = NUM_IMAGES // len(months)

    for mi, month in enumerate(months):
        gallery_dir = base / month
        gallery_dir.mkdir(parents=True, exist_ok=True)
        existing = set(gallery_dir.iterdir())

        for i in range(images_per_month):
            idx = mi * images_per_month + i
            name, (w_ratio, h_ratio) = list(RATIOS.items())[idx % len(RATIOS)]
            w, h = dimensions((w_ratio, h_ratio))
            filename = f"img_{idx:02d}_{name}_{w}x{h}.jpg"
            filepath = gallery_dir / filename

            if filepath in existing:
                print(f"Skipping {month}/{filename} (already exists)")
                continue

            # Spread dates across the month
            day = (i % 28) + 1
            dt = datetime(2025, mi + 1, day, 12, 0, 0) + timedelta(hours=i)

            img = make_image(w, h, seed=idx)
            exif_bytes = make_exif(random.Random(idx), idx, dt)
            img.save(filepath, quality=85, optimize=True, exif=exif_bytes)
            print(f"Created {month}/{filename}  ({(w*h)/1_000_000:.1f}MP, {w}x{h})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the generator**

```bash
python generate_pseudo_imgs.py
```

Expected output: 60 images created across `static/2025-01/`, `static/2025-02/`, `static/2025-03/` (20 each).

- [ ] **Step 3: Commit**

```bash
git add generate_pseudo_imgs.py
git commit -m "feat: multi-gallery pseudo image generator"
```

---

### Task 10: Install dependencies and test

- [ ] **Step 1: Install and run**

```bash
pip install -r requirements.txt
python app.py
```

Expected: Flask dev server starts, visit `http://127.0.0.1:5000/` to see the gallery. Navigate to `/2025-01/`, `/2025-02/`, etc. Test pagination, lightbox, EXIF info, burger menu at <768px.

- [ ] **Step 2: Verify all features**
  - Index shows 10 most recent images
  - Gallery pages show 10 images per gallery
  - Pagination works (Previous/Next)
  - Lightbox opens on click, closes on Escape
  - EXIF card shows camera info
  - Prev/Next navigation works in lightbox
  - Burger menu works at mobile widths
  - Responsive masonry (4 → 3 → 2 → 1 columns)

- [ ] **Step 3: Final commit with any bugfixes**

```bash
git add -A
git commit -m "fix: adjustments after testing"
```
