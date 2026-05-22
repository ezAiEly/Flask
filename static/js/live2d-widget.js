/**
 * Live2D Widget — clean local loader
 * Uses live2d.min.js (Cubism 2 runtime) + local models.
 */
(function() {
  'use strict';

  // ── Model registry (local models in /static/live2d/models/) ──
  var MODELS = [
    { name: 'Pio',              folder: 'Potion-Maker/Pio',              texture: 'default-costume' },
    { name: 'Tia',              folder: 'Potion-Maker/Tia',              texture: 'default-costume' },
    { name: '22 (B站娘)',       folder: 'bilibili-live/22',              texture: 'closet-default-v2' },
    { name: '33 (B站娘)',       folder: 'bilibili-live/33',              texture: 'closet-default-v2' },
    { name: 'Shizuku',          folder: 'ShizukuTalk/shizuku-48',        texture: 'default-costume' },
    { name: 'Shizuku 睡衣',     folder: 'ShizukuTalk/shizuku-pajama',    texture: 'default-costume' },
    { name: 'Neptune',          folder: 'HyperdimensionNeptunia/neptune_classic', texture: 'default-costume' },
    { name: 'Noir',             folder: 'HyperdimensionNeptunia/noir_classic',    texture: 'default-costume' },
    { name: 'Murakumo',         folder: 'KantaiCollection/murakumo',     texture: 'default-costume' }
  ];

  var BASE = '/static/live2d/models/';
  var CDN_BASE = 'https://fastly.jsdelivr.net/gh/fghrsh/live2d_api/model/';

  var currentModel = parseInt(localStorage.getItem('l2d-model') || '0');
  var currentTexture = parseInt(localStorage.getItem('l2d-texture') || '0');
  var visible = localStorage.getItem('l2d-visible') !== 'false';
  var widgetSize = localStorage.getItem('l2d-size') || 'medium';
  var widgetPosition = localStorage.getItem('l2d-position') || 'right';

  if (currentModel >= MODELS.length) currentModel = 0;

  // Size presets
  var SIZE_MAP = { small: 200, medium: 300, large: 400 };

  // ── DOM creation ────────────────────────────────────
  function buildDOM() {
    var html = '';
    // Toggle button (shown when widget is hidden)
    html += '<div id="waifu-toggle"><i class="fas fa-chevron-left"></i> 看板娘</div>';
    // Main widget
    html += '<div id="waifu">';
    html += '  <div id="waifu-tips"></div>';
    html += '  <canvas id="live2d" width="800" height="800"></canvas>';
    html += '  <div id="waifu-tool">';
    html += '    <span id="waifu-tool-switch" title="切换模型"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><path d="M399 384.2C376.9 345.8 335.4 320 288 320H224c-47.4 0-88.9 25.8-111 64.2c35.2 39.2 86.2 63.8 143 63.8s107.8-24.7 143-63.8zM512 256c0 141.4-114.6 256-256 256S0 397.4 0 256S114.6 0 256 0S512 114.6 512 256zM256 272c39.8 0 72-32.2 72-72s-32.2-72-72-72s-72 32.2-72 72s32.2 72 72 72z"/></svg></span>';
    html += '    <span id="waifu-tool-texture" title="切换服装"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><path d="M320 64c0-35.3-28.7-64-64-64s-64 28.7-64 64s28.7 64 64 64s64-28.7 64-64zm-96 96c-35.3 0-64 28.7-64 64v48c0 17.7 14.3 32 32 32h1.8l11.1 99.5c1.8 16.2 15.5 28.5 31.8 28.5h38.7c16.3 0 30-12.3 31.8-28.5L318.2 304H320c17.7 0 32-14.3 32-32V224c0-35.3-28.7-64-64-64H224zM132.3 394.2c13-2.4 21.7-14.9 19.3-27.9s-14.9-21.7-27.9-19.3c-32.4 5.9-60.9 14.2-82 24.8c-10.5 5.3-20.3 11.7-27.8 19.6C6.4 399.5 0 410.5 0 424c0 21.4 15.5 36.1 29.1 45c14.7 9.6 34.3 17.3 56.4 23.4C130.2 504.7 190.4 512 256 512s125.8-7.3 170.4-19.6c22.1-6.1 41.8-13.8 56.4-23.4c13.7-8.9 29.1-23.6 29.1-45c0-13.5-6.4-24.5-14-32.6c-7.5-7.9-17.3-14.3-27.8-19.6c-21-10.6-49.5-18.9-82-24.8c-13-2.4-25.5 6.3-27.9 19.3s6.3 25.5 19.3 27.9c30.2 5.5 53.7 12.8 69 20.5c3.2 1.6 5.8 3.1 7.9 4.5c3.6 2.4 3.6 7.2 0 9.6c-8.8 5.7-23.1 11.8-43 17.3C374.3 457 318.5 464 256 464s-118.3-7-157.7-17.9c-19.9-5.5-34.2-11.6-43-17.3c-3.6-2.4-3.6-7.2 0-9.6c2.1-1.4 4.8-2.9 7.9-4.5c15.3-7.7 38.8-14.9 69-20.5z"/></svg></span>';
    html += '    <span id="waifu-tool-home" title="回到默认模型"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 576 512"><path d="M575.8 255.5c0 18-15 32.1-32 32.1h-32l.7 160.2c0 2.7-.2 5.4-.5 8.1V472c0 22.1-17.9 40-40 40H456c-1.1 0-2.2 0-3.3-.1c-1.4 .1-2.8 .1-4.2 .1H416 392c-22.1 0-40-17.9-40-40V448 384c0-17.7-14.3-32-32-32H256c-17.7 0-32 14.3-32 32v64 24c0 22.1-17.9 40-40 40H160 128.5c-1.5 0-3-.1-4.5-.2c-1.2 .1-2.4 .2-3.6 .2H104c-22.1 0-40-17.9-40-40V360c0-.9 0-1.9 .1-2.8V287.6H32c-18 0-32-14-32-34.1c0-9 3-17 10-24L266.4 8c7-7 15-8 22-8s15 2 21 7L564.8 231.5c8 7 12 15 11 24z"/></svg></span>';
    html += '    <span id="waifu-tool-hide" title="隐藏"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512"><path d="M310.6 150.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L160 210.7 54.6 105.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L114.7 256 9.4 361.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L160 301.3 265.4 406.6c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L205.3 256 310.6 150.6z"/></svg></span>';
    html += '  </div>';
    html += '</div>';
    document.body.insertAdjacentHTML('beforeend', html);
  }

  // ── Tip bubble ──────────────────────────────────────
  var tipTimer = null;
  function showTip(msg, duration) {
    var el = document.getElementById('waifu-tips');
    if (!el || !msg) return;
    if (tipTimer) clearTimeout(tipTimer);
    el.innerHTML = msg;
    el.classList.add('waifu-tips-active');
    tipTimer = setTimeout(function() {
      el.classList.remove('waifu-tips-active');
      tipTimer = null;
    }, duration || 4000);
  }

  // ── Load model ──────────────────────────────────────
  var modelLoading = false;

  function releaseWebGL(canvas) {
    var gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (gl) {
      var ext = gl.getExtension('WEBGL_lose_context');
      if (ext) { ext.loseContext(); return; }
    }
    // Force release: clear the canvas
    canvas.width = canvas.width;
  }

  function loadModel(idx) {
    if (modelLoading) return;
    if (idx >= MODELS.length) idx = 0;
    currentModel = idx;
    localStorage.setItem('l2d-model', idx);
    modelLoading = true;

    var m = MODELS[idx];
    var url = BASE + m.folder + '/index.json';
    console.log('[Live2D] Loading model ' + m.name + ' from ' + url);

    var canvas = document.getElementById('live2d');
    if (!canvas) {
      modelLoading = false;
      return;
    }

    // Release old WebGL context to avoid hitting browser context limit
    releaseWebGL(canvas);

    try {
      loadlive2d('live2d', url);
    } catch(e) {
      console.warn('[Live2D] Local load failed, trying CDN fallback', e);
      loadlive2d('live2d', CDN_BASE + m.folder + '/index.json');
    }

    // Allow next switch after model has time to load
    setTimeout(function() { modelLoading = false; }, 2000);
  }

  function nextModel() {
    if (modelLoading) return;
    var next = (currentModel + 1) % MODELS.length;
    loadModel(next);
    showTip('切换至 ' + MODELS[next].name + ' ~', 3000);
  }

  function resetModel() {
    if (modelLoading) return;
    loadModel(0);
    showTip('回到默认模型啦 ~', 3000);
  }

  // ── Visibility ──────────────────────────────────────
  function show() {
    visible = true;
    localStorage.setItem('l2d-visible', 'true');
    var waifu = document.getElementById('waifu');
    var toggle = document.getElementById('waifu-toggle');
    if (waifu) {
      waifu.style.display = '';
      setTimeout(function() { waifu.style.bottom = '0'; }, 0);
    }
    if (toggle) toggle.classList.remove('waifu-toggle-active');
  }

  function hide() {
    visible = false;
    localStorage.setItem('l2d-visible', 'false');
    var waifu = document.getElementById('waifu');
    var toggle = document.getElementById('waifu-toggle');
    if (waifu) {
      waifu.style.bottom = '-500px';
      setTimeout(function() {
        waifu.style.display = 'none';
        if (toggle) toggle.classList.add('waifu-toggle-active');
      }, 500);
    }
    showTip('有缘再会 ~', 2000);
  }

  // ── Init ────────────────────────────────────────────
  function init() {
    buildDOM();

    // Apply size
    var size = SIZE_MAP[widgetSize] || 300;
    var canvas = document.getElementById('live2d');
    if (canvas) {
      canvas.width = size * 2;
      canvas.height = size * 2;
      canvas.style.width = size + 'px';
      canvas.style.height = size + 'px';
    }

    // Apply position
    var waifuEl = document.getElementById('waifu');
    var toggle = document.getElementById('waifu-toggle');
    if (waifuEl && widgetPosition === 'left') {
      waifuEl.style.right = 'auto';
      waifuEl.style.left = '0';
    }
    if (toggle && widgetPosition === 'left') {
      toggle.classList.add('left');
    }

    // Wire toggle
    toggle.addEventListener('click', function() {
      show();
      loadModel(currentModel);
    });

    // Wire tools
    var toolSwitch = document.getElementById('waifu-tool-switch');
    var toolTexture = document.getElementById('waifu-tool-texture');
    var toolHome = document.getElementById('waifu-tool-home');
    var toolHide = document.getElementById('waifu-tool-hide');

    if (toolSwitch) toolSwitch.addEventListener('click', nextModel);
    if (toolTexture) toolTexture.addEventListener('click', function() {
      showTip('当前仅支持默认服装 ~', 3000);
    });
    if (toolHome) toolHome.addEventListener('click', resetModel);
    if (toolHide) toolHide.addEventListener('click', hide);

    // Initial state
    if (visible) {
      show();
      // loadlive2d needs the canvas to exist before calling
      setTimeout(function() { loadModel(currentModel); }, 100);
    } else {
      var waifu = document.getElementById('waifu');
      if (waifu) waifu.style.display = 'none';
      if (toggle) toggle.classList.add('waifu-toggle-active');
    }

    // Tips on hover over canvas
    var canvas = document.getElementById('live2d');
    if (canvas) {
      canvas.addEventListener('mouseenter', function() {
        var tips = ['诶嘿~', '怎么了？', '喵~', '在看什么呢？', '想和我玩吗？'];
        var tip = tips[Math.floor(Math.random() * tips.length)];
        showTip(tip, 2500);
      });

      // Idle tips every 30s
      var idleTips = [
        '好无聊呀，来看看视频吧~', '今天天气不错呢！', '有什么好看的视频推荐吗？',
        '要不要换个模型看看？点右边按钮试试~', '我可以陪你一起看视频哦！'
      ];
      setInterval(function() {
        if (visible && !tipTimer) {
          var tip = idleTips[Math.floor(Math.random() * idleTips.length)];
          showTip(tip, 5000);
        }
      }, 30000);
    }
  }

  // ── Start ───────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
