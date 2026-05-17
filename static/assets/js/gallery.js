(function () {
  'use strict';

  var lightbox = document.getElementById('lightbox');
  var lightboxImage = document.getElementById('lightbox-image');
  var lightboxInfoCard = document.getElementById('lightbox-info-card');
  var lightboxInfoBtn = document.getElementById('lightbox-info-btn');
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
      ['相机', data.camera],
      ['焦距', data.focal_length],
      ['光圈', data.aperture],
      ['快门速度', data.shutter],
      ['ISO', data.iso],
      ['日期', data.date],
      ['分辨率', data.dimensions],
      ['位置信息', data.location],
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
    lightboxInfoCard.classList.remove('lightbox__info-card--open');
    lightboxInfoCard.innerHTML = '';

    // Fetch EXIF data
    var gallery = card.getAttribute('data-gallery');
    var filename = card.getAttribute('data-filename');
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/exif/' + encodeURIComponent(gallery) + '/' + encodeURIComponent(filename), true);
    xhr.onload = function () {
      if (xhr.status === 200) {
        var data = JSON.parse(xhr.responseText);
        lightboxInfoCard.innerHTML = buildExifTable(data);
      }
    };
    xhr.onerror = function () {
      lightboxInfoCard.innerHTML = '<p style="padding:4px;color:#cc0000;">Failed to load EXIF</p>';
    };
    xhr.send();
  }

  function closeLightbox() {
    lightbox.classList.remove('lightbox--open');
    lightboxInfoCard.classList.remove('lightbox__info-card--open');
    currentIndex = -1;
  }

  // Toggle EXIF info card
  lightboxInfoBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    lightboxInfoCard.classList.toggle('lightbox__info-card--open');
  });

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

  // Close lightbox on background click,
  // navigate on left/right third tap
  lightbox.addEventListener('click', function (e) {
    if (e.target !== lightbox) return;
    var rect = lightbox.getBoundingClientRect();
    var x = e.clientX - rect.left;
    var third = rect.width / 3;
    if (x < third) {
      prevImage();
    } else if (x > rect.width - third) {
      nextImage();
    } else {
      closeLightbox();
    }
  });
})();
