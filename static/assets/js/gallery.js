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
