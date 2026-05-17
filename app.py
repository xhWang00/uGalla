from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request

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
