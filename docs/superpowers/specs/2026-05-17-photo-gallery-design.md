# uGalla — Brutalist Photo Gallery

## Overview

A minimalist, server-side rendered photo gallery built with Flask and Jinja2. Images organized under `static/` in YYYY-MM subfolders are served as paginated gallery pages with a brutalism aesthetic — pure black-and-white, card-based layout with no shadows or fades.

## Architecture

### File Layout

```
uGalla/
├── app.py                  # Flask app: startup cache init, routes, CLI entry
├── gallery.py              # GalleryScanner: walks static/, reads EXIF, caches
├── templates/
│   ├── base.html           # Shell: header, burger menu, content block
│   ├── index.html          # Latest images across all galleries
│   └── gallery.html        # Single gallery (folder) view
├── static/
│   ├── assets/
│   │   ├── css/style.css
│   │   └── js/gallery.js
│   └── imgs/               # (existing, gitignored)
│       └── (YYYY-MM subfolders)
└── requirements.txt
```

### Startup Cache (approach 2)

On app startup, `GalleryScanner` walks all subdirectories under `static/`, reads EXIF metadata from each image via Pillow, sorts by EXIF datetime, and caches in a dict. Routes paginate from cache (10 images per page). A `GalleryScanner.refresh()` method allows re-scanning if needed.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Index — latest images across all galleries, paginated |
| GET | `/<gallery_name>/` | Single gallery page (e.g. `/imgs/`), paginated |
| GET | `/api/exif/<gallery_name>/<filename>` | JSON endpoint returning EXIF data for lightbox |

### API Response Format

`GET /api/exif/<gallery_name>/<filename>` returns JSON:

```json
{
  "camera": "Canon EOS R5",
  "focal_length": "35mm",
  "aperture": "f/2.8",
  "shutter": "1/250",
  "iso": 400,
  "date": "2023-08-15 14:30:00",
  "dimensions": "5963x3354",
  "location": "Tokyo, Japan",
  "filename": "img_00_16x9_5963x3354.jpg"
}
```

## Data Flow

1. `GalleryScanner.__init__()` scans `static/` on startup
2. For each subdirectory (gallery), walks image files and extracts EXIF via `PIL.Image._getexif()`
3. Images sorted by EXIF DateTimeOriginal (descending)
4. Cached as `dict[gallery_name, list[ImageMeta]]`
5. Routes slice from cache using `page` query param (1-based, 10 per page)
6. `/api/exif/<path>` returns JSON for a single image

## Frontend

### Design System

- **Typography:** JetBrains Mono (monospace, brutalism)
- **Color:** `#000` on `#fff`. Accent: `#cc0000` for hover/active states
- **Cards:** `border: 1px solid #000; padding: 8px; background: #fff;` — flat, no radius, no shadow
- **Masonry:** CSS `columns` layout with `column-count`:
  - 4 cols ≥1200px
  - 3 cols ≥768px
  - 2 cols ≥480px
  - 1 col <480px
- **Breakpoints:** 480px, 768px, 1200px

### Header Bar

- Fixed top, white background, `border-bottom: 1px solid #000`
- Left: site title "uGalla" (links to index)
- Right: horizontal nav links to each gallery folder + "All" link for index
- **Mobile (<768px):** collapsed into CSS-only hamburger toggle

### Pagination

- Previous / Next links at page bottom
- "Page X of Y" indicator
- Query param: `?page=N`

### Lightbox

- Full-screen overlay, `rgba(0,0,0,.85)` background
- Image centered, `max-width: 90vw; max-height: 85vh`
- Prev (◀) / Next (▶) arrows for gallery navigation
- Close via X button or Escape key
- EXIF info card: slides up from bottom on "i" icon click
  - Camera make/model, focal length, aperture, shutter speed, ISO
  - Date taken, dimensions, GPS city/country
- Data fetched from `/api/exif/<path>` endpoint

### Responsive Behavior

- Masonry columns adjust via media queries
- Burger menu replaces nav links on <768px
- Lightbox works on touch: tap sides for prev/next, tap center for close

## Implementation Plan

1. Create `requirements.txt` with Flask, Pillow
2. Implement `gallery.py` — GalleryScanner with startup cache
3. Implement `app.py` — Flask app with routes
4. Create `templates/base.html` — header + burger + content block
5. Create `templates/index.html` — paginated latest images
6. Create `templates/gallery.html` — paginated gallery view
7. Create `static/assets/css/style.css` — brutalism styling
8. Create `static/assets/js/gallery.js` — lightbox + EXIF fetch + masonry
9. Run and test with existing `static/imgs/` data
10. Regenerate test images into YYYY-MM subfolders for multi-gallery testing
