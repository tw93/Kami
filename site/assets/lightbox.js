// Every picture on the home page opens in place: a document shows all of its
// pages and a link to its PDF, the social cards and the product sites open as
// galleries of their own row. PhotoSwipe (about 70KB) loads when the page is
// idle or a pointer reaches a picture; a click that lands first is remembered
// and opened once it is ready.
(function () {
  var docLinks = [].slice.call(document.querySelectorAll('a[data-pages]'));
  var rowImgs = [].slice.call(document.querySelectorAll('.demo-grid.one-line .demo-card > img, .landing-card > img'));
  if (!docLinks.length && !rowImgs.length) return;

  var lang = (document.documentElement.lang || 'en').toLowerCase();
  var T = {
    en: ['Download PDF', 'Close', 'Zoom', 'Previous', 'Next'],
    'zh-cn': ['下载 PDF', '关闭', '缩放', '上一页', '下一页'],
    'zh-tw': ['下載 PDF', '關閉', '縮放', '上一頁', '下一頁'],
    ja: ['PDF をダウンロード', '閉じる', '拡大', '前へ', '次へ'],
    ko: ['PDF 다운로드', '닫기', '확대', '이전', '다음']
  };
  var t = T[lang] || T[lang.slice(0, 2)] || T.en;
  var base = document.currentScript ? document.currentScript.src.replace(/[^/]*$/, '') : 'assets/';
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var state = 'idle';
  var pending = null;
  var lightbox = null;
  var currentPdf = '';

  function loadScript(src, done) {
    var s = document.createElement('script');
    s.src = src;
    s.onload = done;
    document.head.appendChild(s);
  }

  function load() {
    if (state !== 'idle') return;
    state = 'loading';
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = base + 'vendor/photoswipe/photoswipe.css';
    document.head.appendChild(link);
    loadScript(base + 'vendor/photoswipe/photoswipe.umd.min.js', function () {
      loadScript(base + 'vendor/photoswipe/photoswipe-lightbox.umd.min.js', init);
    });
  }

  function size(img) {
    return {
      w: Number(img.getAttribute('width')) || img.naturalWidth || 1600,
      h: Number(img.getAttribute('height')) || img.naturalHeight || 1200
    };
  }

  // A document: every page rendered from its PDF, the card's picture as the
  // first page's placeholder so the zoom starts from it.
  function docSource(a) {
    var pdf = a.getAttribute('href');
    var name = pdf.replace(/^.*\//, '').replace(/\.pdf$/, '');
    var dir = pdf.replace(/[^/]*$/, '');
    var count = Number(a.getAttribute('data-pages')) || 1;
    var wide = a.hasAttribute('data-landscape');
    var thumb = a.querySelector('img');
    var items = [];
    for (var i = 1; i <= count; i++) {
      items.push({
        src: dir + 'pages/' + name + '-' + i + '.webp',
        width: wide ? 2263 : 1600,
        height: wide ? 1600 : 2263,
        alt: (thumb ? thumb.alt : name) + ' ' + i + ' / ' + count,
        element: i === 1 && !wide ? thumb : undefined,
        msrc: i === 1 && !wide ? thumb.currentSrc || thumb.src : undefined
      });
    }
    return { items: items, pdf: pdf, fade: wide };
  }

  function rowSource(img) {
    var row = [].slice.call(img.closest('.demo-grid, .landing-grid').querySelectorAll('img'));
    return {
      index: row.indexOf(img),
      items: row.map(function (el) {
        var s = size(el);
        return { src: el.currentSrc || el.src, width: s.w, height: s.h, alt: el.alt, element: el, msrc: el.currentSrc || el.src };
      })
    };
  }

  function open(target) {
    var src = target.tagName === 'A' ? docSource(target) : rowSource(target);
    currentPdf = src.pdf || '';
    lightbox.options.showHideAnimationType = reduce ? 'none' : src.fade ? 'fade' : 'zoom';
    lightbox.options.dataSource = src.items;
    lightbox.loadAndOpen(src.index || 0);
  }

  function init() {
    if (typeof PhotoSwipeLightbox === 'undefined' || typeof PhotoSwipe === 'undefined') return;
    lightbox = new PhotoSwipeLightbox({
      pswpModule: PhotoSwipe,
      bgOpacity: 0.92,
      padding: { top: 56, bottom: 32, left: 24, right: 24 },
      wheelToZoom: false,
      closeTitle: t[1],
      zoomTitle: t[2],
      arrowPrevTitle: t[3],
      arrowNextTitle: t[4],
      showAnimationDuration: reduce ? 0 : 333,
      hideAnimationDuration: reduce ? 0 : 333,
      zoomAnimationDuration: reduce ? 0 : 333
    });
    lightbox.addFilter('thumbEl', function (thumbEl, data) {
      return data.element || thumbEl;
    });
    lightbox.addFilter('placeholderSrc', function (src, content) {
      return content.data.msrc || src;
    });
    lightbox.on('uiRegister', function () {
      if (!currentPdf) return;
      lightbox.pswp.ui.registerElement({
        name: 'download',
        order: 8,
        isButton: true,
        tagName: 'a',
        title: t[0],
        ariaLabel: t[0],
        html: {
          isCustomSVG: true,
          inner: '<path d="M20.5 14.3 17.1 18V10h-2.2v7.9l-3.4-3.6L10 16l6 6.1 6-6.1ZM23 23H9v2h14Z" id="pswp__icn-download"/>',
          outlineID: 'pswp__icn-download'
        },
        onInit: function (el) {
          el.setAttribute('href', currentPdf);
          el.setAttribute('download', '');
        }
      });
    });
    keepCorners(lightbox, 8);
    lightbox.init();
    state = 'ready';
    if (pending) {
      open(pending);
      pending = null;
    }
  }

  function onClick(e) {
    // Modified clicks keep the link's own behaviour: a new tab for the PDF.
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button) return;
    e.preventDefault();
    if (state === 'ready') return open(e.currentTarget);
    pending = e.currentTarget;
    load();
  }

  docLinks.concat(rowImgs).forEach(function (el) {
    el.addEventListener('click', onClick);
    el.addEventListener('pointerover', load, { once: true });
    el.addEventListener('touchstart', load, { passive: true, once: true });
  });
  if ('requestIdleCallback' in window) requestIdleCallback(load, { timeout: 3000 });
  else setTimeout(load, 1500);

  // PhotoSwipe zooms by scaling its wrap, which would scale the 8px corners
  // too. The wrap carries --pswp-img-radius = radius / scale, set in the same
  // task PhotoSwipe writes a transform, and while a transition runs one script
  // animation replays that transform together with the radius, so a stalled
  // main thread pauses both instead of letting the corners swell. Same recipe
  // as tw93.fun's js/index.js keepLightboxCorners.
  function keepCorners(lb, radius) {
    if (!Element.prototype.animate || !Element.prototype.getAnimations) return;
    var scaleOf = function (tf) {
      return (tf && tf !== 'none' ? new DOMMatrixReadOnly(tf).a : 1) || 1;
    };
    var setRadius = function (wrap, scale) {
      wrap.style.setProperty('--pswp-img-radius', radius / scale + 'px');
    };
    var isRadius = function (a) {
      return a.id === 'pswp-radius';
    };
    var syncWrap = function (wrap) {
      if (!wrap || wrap.getAnimations().some(isRadius)) return;
      setRadius(wrap, scaleOf(getComputedStyle(wrap).transform));
    };
    var syncSlides = function () {
      if (!lb.pswp) return;
      lb.pswp.mainScroll.itemHolders.forEach(function (h) {
        if (h.slide && h.slide.container) syncWrap(h.slide.container);
      });
    };
    document.addEventListener('transitionrun', function (event) {
      var wrap = event.target;
      if (event.propertyName !== 'transform' || !wrap.classList || !wrap.classList.contains('pswp__zoom-wrap')) return;
      var tr = wrap.getAnimations().filter(function (a) {
        return a.transitionProperty === 'transform';
      })[0];
      var effect = tr && tr.effect;
      if (!effect) return;
      var kf = effect.getKeyframes();
      var target = new DOMMatrixReadOnly(wrap.style.transform || 'none');
      var start = new DOMMatrix(String(kf[0].transform));
      var end = new DOMMatrixReadOnly(String(kf[kf.length - 1].transform));
      var zoom = Math.abs(target.e) >= Math.abs(target.f) ? end.e / target.e : end.f / target.f;
      if (!isFinite(zoom) || zoom <= 0) return;
      start.e /= zoom;
      start.f /= zoom;
      var from = start.a;
      var to = target.a;
      var timing = effect.getTiming();
      wrap.getAnimations().forEach(function (a) {
        if (isRadius(a)) a.cancel();
      });
      var steps = 24;
      var frames = [];
      for (var i = 0; i <= steps; i++) {
        frames.push({ offset: i / steps, '--pswp-img-radius': radius / (from + ((to - from) * i) / steps) + 'px' });
      }
      frames[0].transform = start.toString();
      frames[steps].transform = target.toString();
      var anim = wrap.animate(frames, { duration: timing.duration, easing: timing.easing, id: 'pswp-radius' });
      setRadius(wrap, to);
      var align = function () {
        if (tr.startTime !== null) anim.startTime = tr.startTime;
      };
      align();
      tr.ready.then(align, function () {});
      tr.finished.then(
        function () {
          anim.cancel();
        },
        function () {
          anim.cancel();
          syncWrap(wrap);
        }
      );
    });
    lb.on('beforeOpen', syncSlides);
    lb.on('openingAnimationStart', syncSlides);
    lb.on('zoomPanUpdate', syncSlides);
    lb.on('change', syncSlides);
    lb.on('contentResize', function (e) {
      var ph = e.content.placeholder && e.content.placeholder.element;
      if (ph && ph.tagName === 'IMG') ph.style.setProperty('--pswp-ph-scale', String(e.width / 250 || 1));
    });
  }
})();
