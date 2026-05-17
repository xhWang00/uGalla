from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image


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
    if isinstance(dms[0], tuple):
        deg = float(dms[0][0]) / float(dms[0][1]) if dms[0][1] else 0
        minute = float(dms[1][0]) / float(dms[1][1]) if dms[1][1] else 0
        sec = float(dms[2][0]) / float(dms[2][1]) if dms[2][1] else 0
    else:
        deg = float(dms[0])
        minute = float(dms[1])
        sec = float(dms[2])
    decimal = deg + minute / 60.0 + sec / 3600.0
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def _rational_to_float(val: object) -> float:
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


def _parse_shutter(rational: object) -> str:
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
            with Image.open(fpath) as img:
                w, h = img.size
                exif_data = img.getexif()
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
                if EXIF_MAKE in exif_data:
                    camera_make = str(exif_data[EXIF_MAKE]).strip()
                if EXIF_MODEL in exif_data:
                    camera_model = str(exif_data[EXIF_MODEL]).strip()

                exif_ifd = exif_data.get_ifd(34665)
                if EXIF_DATETIME_ORIGINAL in exif_ifd:
                    date_taken = str(exif_ifd[EXIF_DATETIME_ORIGINAL])
                if EXIF_FOCAL_LENGTH in exif_ifd:
                    fl = _rational_to_float(exif_ifd[EXIF_FOCAL_LENGTH])
                    focal_length = f"{int(fl)}mm" if fl else None
                if EXIF_FNUMBER in exif_ifd:
                    ap = _rational_to_float(exif_ifd[EXIF_FNUMBER])
                    aperture = f"f/{ap}" if ap else None
                if EXIF_EXPOSURE_TIME in exif_ifd:
                    shutter = _parse_shutter(exif_ifd[EXIF_EXPOSURE_TIME])
                if EXIF_ISO in exif_ifd:
                    iso = int(exif_ifd[EXIF_ISO])

                gps_info = exif_data.get_ifd(GPS_INFO_TAG)
                if gps_info:
                    lat_dms = gps_info.get(GPS_LAT_TAG)
                    lat_ref = gps_info.get(GPS_LAT_REF_TAG, b"N")
                    lon_dms = gps_info.get(GPS_LON_TAG)
                    lon_ref = gps_info.get(GPS_LON_REF_TAG, b"E")
                    if isinstance(lat_ref, bytes):
                        lat_ref = lat_ref.decode()
                    if isinstance(lon_ref, bytes):
                        lon_ref = lon_ref.decode()
                    if lat_dms and lon_dms:
                        gps_lat = round(_dms_to_decimal(lat_dms, lat_ref), 6)
                        gps_lon = round(_dms_to_decimal(lon_dms, lon_ref), 6)

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
        page = max(1, page)
        start = (page - 1) * per_page
        end = start + per_page
        return images[start:end], total

    def get_latest(self, page: int = 1, per_page: int = 10) -> tuple[list[ImageMeta], int]:
        all_images: list[ImageMeta] = []
        for g in self._gallery_order:
            all_images.extend(self._galleries[g])
        all_images.sort(key=lambda m: m.date_taken or "", reverse=True)
        total = len(all_images)
        page = max(1, page)
        start = (page - 1) * per_page
        end = start + per_page
        return all_images[start:end], total

    def get_exif(self, gallery: str, filename: str) -> Optional[dict]:
        images = self._galleries.get(gallery, [])
        for img in images:
            if img.filename == filename:
                location = None
                if img.location_city and img.location_country:
                    location = f"{img.location_city}, {img.location_country}"
                elif img.gps_lat is not None and img.gps_lon is not None:
                    location = f"{img.gps_lat:.4f}, {img.gps_lon:.4f}"
                return {
                    "camera": f"{img.camera_make or ''} {img.camera_model or ''}".strip(),
                    "focal_length": img.focal_length,
                    "aperture": img.aperture,
                    "shutter": img.shutter,
                    "iso": img.iso,
                    "date": img.date_taken,
                    "dimensions": f"{img.width}x{img.height}",
                    "location": location,
                    "path": img.path,
                    "filename": img.filename,
                }
        return None
