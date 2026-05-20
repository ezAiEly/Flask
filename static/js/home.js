(function () {
  'use strict';

  var grid = document.getElementById('videoGrid');
  var statusEl = document.getElementById('homeStatus');
  var loadMoreWrap = document.getElementById('loadMoreWrap');
  var loadMoreBtn = document.getElementById('loadMoreBtn');
  var emptyState = document.getElementById('emptyState');
  var tabs = document.querySelectorAll('.home-tab');

  var currentTab = 'recommend';
  var currentPage = 1;
  var hasMore = false;
  var loading = false;

  // ── Hero Carousel ─────────────────────────────────────

  var heroSwiper = null;

  function initCarousel() {
    fetch('/api/videos/hot?page=1&limit=8')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var videos = data.videos || [];
        if (!videos.length) return;
        var slides = document.getElementById('heroSlides');
        slides.innerHTML = '';
        videos.forEach(function (v) {
          var slide = document.createElement('div');
          slide.className = 'swiper-slide';
          var bg = v.cover_image
            ? 'url(/static/covers/' + escapeHtml(v.cover_image) + ')'
            : '';
          if (bg) {
            slide.style.backgroundImage = bg;
          } else {
            slide.classList.add('hero-slide-no-cover');
          }
          slide.innerHTML =
            '<a href="/video/' + v.id + '" class="hero-slide-link">' +
              '<div class="hero-slide-overlay"></div>' +
              '<div class="hero-slide-info">' +
                '<h3>' + escapeHtml(v.title) + '</h3>' +
                '<p>' + escapeHtml(v.author ? v.author.username : '') + ' · ' + formatCount(v.views) + ' 次播放</p>' +
              '</div>' +
            '</a>';
          slides.appendChild(slide);
        });
        heroSwiper = new Swiper('#heroCarousel', {
          loop: true,
          autoplay: { delay: 4000, disableOnInteraction: false },
          pagination: { el: '.swiper-pagination', clickable: true },
          navigation: { nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' }
        });
      })
      .catch(function () { /* carousel load failed, non-critical */ });
  }

  initCarousel();

  // ── Tab switching ────────────────────────────────────

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      var name = this.dataset.tab;
      if (name === currentTab) return;
      tabs.forEach(function (t) { t.classList.remove('active'); });
      this.classList.add('active');
      currentTab = name;
      resetAndLoad();
    });
  });

  // ── Init ─────────────────────────────────────────────

  resetAndLoad();

  // ── Load more ────────────────────────────────────────

  loadMoreBtn.addEventListener('click', function () {
    if (loading) return;
    currentPage++;
    fetchVideos(false);
  });

  // ── Core ─────────────────────────────────────────────

  function resetAndLoad() {
    currentPage = 1;
    hasMore = false;
    grid.innerHTML = '';
    emptyState.classList.add('hidden');
    loadMoreWrap.classList.add('hidden');
    showLoading(true);
    fetchVideos(true);
  }

  function fetchVideos(reset) {
    loading = true;
    var url;
    if (currentTab === 'recommend') {
      url = '/api/videos/recommend?page=' + currentPage + '&limit=12';
    } else {
      url = '/api/videos/hot?page=' + currentPage + '&limit=12';
    }

    fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        var videos = data.videos || [];
        hasMore = data.has_more;

        if (reset) showLoading(false);

        if (videos.length === 0 && reset) {
          emptyState.classList.remove('hidden');
          return;
        }

        renderCards(videos);

        if (hasMore) {
          loadMoreWrap.classList.remove('hidden');
        } else {
          loadMoreWrap.classList.add('hidden');
        }
      })
      .catch(function (err) {
        console.error('加载视频失败:', err);
        if (reset) {
          showLoading(false);
          statusEl.innerHTML = '<p class="text-muted">加载失败，请刷新重试</p>';
        }
        showToast('加载失败，请重试', 'error');
      })
      .finally(function () {
        loading = false;
      });
  }

  // ── Render ───────────────────────────────────────────

  function renderCards(videos) {
    videos.forEach(function (v) {
      var card = document.createElement('a');
      card.className = 'video-card';
      card.href = '/video/' + v.id;

      var tagsHtml = '';
      if (v.tags && v.tags.length > 0) {
        tagsHtml = '<div class="vc-tags">' +
          v.tags.slice(0, 3).map(function (t) {
            return '<span class="vc-tag">' + escapeHtml(t) + '</span>';
          }).join('') +
          '</div>';
      }

      card.innerHTML =
        '<div class="video-card-thumb">' +
          (v.cover_image ? '<img src="/static/covers/' + escapeHtml(v.cover_image) + '" alt="" loading="lazy">' : '<i class="fas fa-play-circle"></i>') +
          (v.duration_hms
            ? '<span class="video-card-duration">' + escapeHtml(v.duration_hms) + '</span>'
            : '') +
        '</div>' +
        '<div class="video-card-body">' +
          '<h3>' + escapeHtml(v.title) + '</h3>' +
          '<div class="meta">' +
            '<span><i class="fas fa-user"></i> ' + escapeHtml(v.author.username) + '</span>' +
            '<span><i class="fas fa-eye"></i> ' + formatCount(v.views) + '</span>' +
            '<span><i class="fas fa-comment"></i> ' + formatCount(v.danmaku_count || 0) + '</span>' +
          '</div>' +
          tagsHtml +
        '</div>';

      grid.appendChild(card);
    });
  }

  // ── Helpers ──────────────────────────────────────────

  function showLoading(on) {
    if (on) {
      statusEl.classList.remove('hidden');
      statusEl.innerHTML = '<div class="spinner spinner-dark"></div><p class="text-muted">加载中…</p>';
    } else {
      statusEl.classList.add('hidden');
    }
  }

  function formatCount(n) {
    if (n >= 10000) return (n / 10000).toFixed(1) + '万';
    return String(n);
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }
})();
