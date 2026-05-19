/**
 * InteractionBar — 视频互动栏（点赞/投币/收藏/分享）
 * 用法：new InteractionBar({ container, videoId, loggedIn })
 */
(function () {
  'use strict';

  var ACTION_LABELS = {
    like: '点赞',
    liked: '已赞',
    coin: '投币',
    coined: '已投币',
    favorite: '收藏',
    favorited: '已收藏',
    share: '分享'
  };

  function InteractionBar(opts) {
    this.videoId = opts.videoId;
    this.loggedIn = opts.loggedIn || false;
    this.container = typeof opts.container === 'string'
      ? document.querySelector(opts.container)
      : opts.container;
    this._state = { liked: false, coined: false, favorited: false, myCoins: 0 };
    this._counts = { like_count: 0, coin_count: 0, favorite_count: 0 };
    this._build();
    this._load();
  }

  InteractionBar.prototype._build = function () {
    var self = this;
    var h = '';
    h += '<div class="interaction-bar">';

    // Like
    h += '<button class="ib-btn" data-action="like" title="点赞">';
    h += '<i class="fas fa-thumbs-up"></i>';
    h += '<span class="ib-count" data-count="like">0</span>';
    h += '</button>';

    // Coin
    h += '<div class="ib-coin-wrap">';
    h += '<button class="ib-btn" data-action="coin" title="投币">';
    h += '<i class="fas fa-coins"></i>';
    h += '<span class="ib-count" data-count="coin">0</span>';
    h += '</button>';
    h += '<div class="ib-coin-popup">';
    h += '<button data-coin="1">投 1 币</button>';
    h += '<button data-coin="2">投 2 币</button>';
    h += '</div>';
    h += '</div>';

    // Favorite
    h += '<button class="ib-btn" data-action="favorite" title="收藏">';
    h += '<i class="fas fa-star"></i>';
    h += '<span class="ib-count" data-count="favorite">0</span>';
    h += '</button>';

    // Share
    h += '<button class="ib-btn" data-action="share" title="分享">';
    h += '<i class="fas fa-share"></i>';
    h += '</button>';

    h += '</div>';
    this.container.innerHTML = h;

    this._els = {
      like: this.container.querySelector('[data-action="like"]'),
      coin: this.container.querySelector('[data-action="coin"]'),
      favorite: this.container.querySelector('[data-action="favorite"]'),
      share: this.container.querySelector('[data-action="share"]'),
      coinPopup: this.container.querySelector('.ib-coin-popup'),
      countLike: this.container.querySelector('[data-count="like"]'),
      countCoin: this.container.querySelector('[data-count="coin"]'),
      countFav: this.container.querySelector('[data-count="favorite"]')
    };

    var btns = this._els;
    btns.like.addEventListener('click', function () { self._act('like'); });
    btns.favorite.addEventListener('click', function () { self._act('favorite'); });

    // Coin: toggle popup
    btns.coin.addEventListener('click', function (e) {
      e.stopPropagation();
      if (!self.loggedIn) { showToast('请先登录', 'error'); return; }
      var popup = self._els.coinPopup;
      if (popup.classList.contains('show')) {
        popup.classList.remove('show');
      } else {
        popup.classList.add('show');
      }
    });

    // Coin popup options
    var coinBtns = this.container.querySelectorAll('.ib-coin-popup button');
    coinBtns.forEach(function (b) {
      b.addEventListener('click', function (e) {
        e.stopPropagation();
        self._act('coin', parseInt(b.dataset.coin));
        self._els.coinPopup.classList.remove('show');
      });
    });

    // Close coin popup on outside click
    document.addEventListener('click', function () {
      self._els.coinPopup.classList.remove('show');
    });

    // Share: copy URL
    btns.share.addEventListener('click', function () {
      var url = window.location.href;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(function () {
          showToast('链接已复制到剪贴板', 'success');
        });
      } else {
        var ta = document.createElement('textarea');
        ta.value = url;
        ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showToast('链接已复制到剪贴板', 'success');
      }
    });
  };

  InteractionBar.prototype._load = function () {
    var self = this;
    fetch('/api/video/' + this.videoId + '/interactions')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        self._counts = {
          like_count: d.like_count || 0,
          coin_count: d.coin_count || 0,
          favorite_count: d.favorite_count || 0
        };
        if (d.hasOwnProperty('liked')) {
          self._state.liked = d.liked;
          self._state.coined = d.coined;
          self._state.favorited = d.favorited;
          self._state.myCoins = d.my_coins || 0;
        }
        self._render();
      });
  };

  InteractionBar.prototype._act = function (action, coinCount) {
    if (!this.loggedIn) { showToast('请先登录', 'error'); return; }

    var self = this;
    var body = undefined;
    if (action === 'coin') {
      body = JSON.stringify({ count: coinCount || 1 });
    }

    fetch('/api/video/' + this.videoId + '/' + action, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.error) { showToast(d.error, 'error'); return; }

        if (action === 'like') {
          self._state.liked = d.liked;
          self._counts.like_count = d.like_count;
          if (d.liked) self._bounce(self._els.like);
        } else if (action === 'coin') {
          self._state.coined = true;
          self._state.myCoins = d.coin_count;
          self._counts.coin_count = d.total_coins;
          self._bounce(self._els.coin);
        } else if (action === 'favorite') {
          self._state.favorited = d.favorited;
          self._counts.favorite_count = d.favorite_count;
          if (d.favorited) self._bounce(self._els.favorite);
        }
        self._render();
      })
      .catch(function () { showToast('网络错误', 'error'); });
  };

  InteractionBar.prototype._bounce = function (el) {
    el.classList.add('ib-bounce');
    setTimeout(function () { el.classList.remove('ib-bounce'); }, 400);
  };

  InteractionBar.prototype._render = function () {
    var s = this._state, c = this._counts;
    this._els.countLike.textContent = c.like_count || '';
    this._els.countCoin.textContent = c.coin_count || '';
    this._els.countFav.textContent = c.favorite_count || '';

    this._els.like.classList.toggle('active', s.liked);
    this._els.coin.classList.toggle('active', s.coined);
    this._els.favorite.classList.toggle('active', s.favorited);
  };

  window.InteractionBar = InteractionBar;
})();
