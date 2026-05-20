/**
 * 看板娘 — 2D chibi mascot with mouse tracking, drag, speech bubbles
 * Customizable: settings panel, import custom image, persist position/preferences
 */
(function () {
  'use strict';

  var MESSAGES = [
    '欢迎来到视频社区~',
    '今天看点什么好呢？',
    '记得点赞投币哦！',
    '有新的视频上线啦',
    '常来看看呀~',
    '好无聊，陪我玩会儿嘛',
    '你知道吗？这里有好多好玩的游戏',
    '有什么想看的视频吗？',
    '喵~',
    '要不要玩个小游戏？',
  ];

  var SETTINGS_KEY = 'mascot_settings';
  var defaultSettings = {
    visible: true,
    speechEnabled: true,
    speechFreqMin: 8,
    speechFreqMax: 20,
    idleAnim: true,
    x: window.innerWidth - 90,
    y: window.innerHeight - 140,
    imageUrl: ''
  };
  var settings = {};

  function loadSettings() {
    var saved = {};
    try {
      var raw = localStorage.getItem(SETTINGS_KEY);
      if (raw) saved = JSON.parse(raw);
    } catch(e) {}
    // Merge with defaults (handles new keys added in future)
    settings = Object.assign({}, defaultSettings, saved);
  }

  function saveSettings() {
    settings.x = pos.x;
    settings.y = pos.y;
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    } catch(e) {}
  }

  var el = null, bubble = null, panel = null;
  var pos = { x: 0, y: 0 };
  var target = { x: 0, y: 0 };
  var dragging = false;
  var dragOff = { x: 0, y: 0 };
  var mouse = { x: 0, y: 0 };
  var animId = null;
  var bubbleTimer = null;
  var idleTime = 0;

  function init() {
    loadSettings();

    pos.x = settings.x;
    pos.y = settings.y;
    target.x = pos.x;
    target.y = pos.y;

    buildDOM();
    bindEvents();
    applySettings();
    loop();
    if (settings.speechEnabled) scheduleBubble();
  }

  function buildDOM() {
    // Container
    el = document.createElement('div');
    el.className = 'mascot';
    el.style.cssText = 'left:' + pos.x + 'px;top:' + pos.y + 'px;';
    el.innerHTML =
      '<div class="mascot-body">' +
        '<div class="mascot-hair"></div>' +
        '<div class="mascot-hair-back"></div>' +
        '<div class="mascot-face">' +
          '<div class="mascot-eye mascot-eye-left">' +
            '<div class="mascot-pupil"></div>' +
          '</div>' +
          '<div class="mascot-eye mascot-eye-right">' +
            '<div class="mascot-pupil"></div>' +
          '</div>' +
          '<div class="mascot-blush mascot-blush-left"></div>' +
          '<div class="mascot-blush mascot-blush-right"></div>' +
          '<div class="mascot-mouth"></div>' +
        '</div>' +
        '<div class="mascot-arm mascot-arm-left"></div>' +
        '<div class="mascot-arm mascot-arm-right"></div>' +
      '</div>';

    // Speech bubble
    bubble = document.createElement('div');
    bubble.className = 'mascot-bubble';
    bubble.textContent = '你好呀~';
    el.appendChild(bubble);

    // Tooltip
    var tip = document.createElement('div');
    tip.className = 'mascot-tip';
    tip.textContent = '拖拽可移动 · 点击可切换表情';
    el.appendChild(tip);

    // Gear button
    var gear = document.createElement('button');
    gear.className = 'mascot-gear';
    gear.title = '看板娘设置';
    gear.innerHTML = '<i class="fas fa-cog"></i>';
    gear.addEventListener('click', function (e) {
      e.stopPropagation();
      togglePanel();
    });
    el.appendChild(gear);

    // Control panel
    panel = document.createElement('div');
    panel.className = 'mascot-panel';
    panel.innerHTML =
      '<h4>看板娘设置</h4>' +
      '<label><input type="checkbox" id="mpVisible" checked> 显示看板娘</label>' +
      '<label><input type="checkbox" id="mpSpeech" checked> 气泡消息</label>' +
      '<label>气泡间隔: <input type="range" id="mpSpeechFreq" min="5" max="30" value="10"> <span id="mpFreqLabel">10s</span></label>' +
      '<label><input type="checkbox" id="mpIdleAnim" checked> 待机动画</label>' +
      '<hr>' +
      '<label style="display:block;margin-bottom:4px;">自定义角色图片:</label>' +
      '<input type="file" id="mpImageInput" accept="image/png,image/gif,image/webp" style="margin-bottom:4px;">' +
      '<button id="mpResetImage" class="btn btn-outline btn-sm" style="margin-top:4px;width:100%;">恢复默认角色</button>' +
      '<hr>' +
      '<button id="mpSaveSettings" class="btn btn-primary btn-sm" style="width:100%;">保存设置</button>';
    el.appendChild(panel);

    // Apply custom image if set
    if (settings.imageUrl) applyCustomImage(settings.imageUrl);

    document.body.appendChild(el);
  }

  function applyCustomImage(url) {
    // Remove existing custom image if any
    var existing = el.querySelector('.mascot-custom-img');
    if (existing) existing.remove();
    if (!url) return;
    var img = document.createElement('img');
    img.className = 'mascot-custom-img';
    img.src = url;
    img.alt = '自定义看板娘';
    el.querySelector('.mascot-body').appendChild(img);
  }

  function bindEvents() {
    document.addEventListener('mousemove', function (e) {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      idleTime = 0;
    });

    // Drag — mouse
    el.addEventListener('mousedown', function (e) {
      if (e.button !== 0) return;
      if (e.target.closest('.mascot-gear') || e.target.closest('.mascot-panel')) return;
      dragging = true;
      var rect = el.getBoundingClientRect();
      dragOff.x = e.clientX - rect.left - rect.width / 2;
      dragOff.y = e.clientY - rect.top - rect.height / 2;
      el.classList.add('dragging');
      hideBubble();
      hidePanel();
    });

    // Drag — touch
    el.addEventListener('touchstart', function (e) {
      if (e.target.closest('.mascot-gear') || e.target.closest('.mascot-panel')) return;
      dragging = true;
      var rect = el.getBoundingClientRect();
      dragOff.x = e.touches[0].clientX - rect.left - rect.width / 2;
      dragOff.y = e.touches[0].clientY - rect.top - rect.height / 2;
      el.classList.add('dragging');
      hideBubble();
      hidePanel();
    }, { passive: true });

    window.addEventListener('mousemove', function (e) {
      if (!dragging) return;
      target.x = e.clientX - dragOff.x;
      target.y = e.clientY - dragOff.y;
      clampTarget();
    });

    window.addEventListener('touchmove', function (e) {
      if (!dragging) return;
      target.x = e.touches[0].clientX - dragOff.x;
      target.y = e.touches[0].clientY - dragOff.y;
      clampTarget();
    }, { passive: true });

    window.addEventListener('mouseup', endDrag);
    window.addEventListener('touchend', endDrag);

    // Click to toggle expression (only when not interacting with controls)
    el.addEventListener('click', function (e) {
      if (dragging) return;
      if (e.target.closest('.mascot-gear') || e.target.closest('.mascot-panel')) return;
      el.classList.toggle('happy');
      setTimeout(function () { el.classList.remove('happy'); }, 1200);
      var msg = MESSAGES[Math.floor(Math.random() * MESSAGES.length)];
      showBubble(msg);
    });

    // Panel events
    panel.addEventListener('click', function (e) {
      e.stopPropagation();
    });

    var visibleCb = document.getElementById('mpVisible');
    var speechCb = document.getElementById('mpSpeech');
    var freqSlider = document.getElementById('mpSpeechFreq');
    var freqLabel = document.getElementById('mpFreqLabel');
    var idleCb = document.getElementById('mpIdleAnim');
    var imageInput = document.getElementById('mpImageInput');
    var resetBtn = document.getElementById('mpResetImage');
    var saveBtn = document.getElementById('mpSaveSettings');

    freqSlider.addEventListener('input', function () {
      if (freqLabel) freqLabel.textContent = freqSlider.value + 's';
    });

    // Preview image
    imageInput.addEventListener('change', function () {
      var file = imageInput.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function (ev) {
        applyCustomImage(ev.target.result);
      };
      reader.readAsDataURL(file);
    });

    saveBtn.addEventListener('click', function () {
      settings.visible = visibleCb.checked;
      settings.speechEnabled = speechCb.checked;
      settings.speechFreqMin = parseInt(freqSlider.value);
      settings.speechFreqMax = parseInt(freqSlider.value) + 5;
      settings.idleAnim = idleCb.checked;
      applySettings();

      // Upload custom image if selected
      var file = imageInput.files[0];
      if (file) {
        uploadMascotImage(file);
      }
      saveSettings();
      hidePanel();
    });

    resetBtn.addEventListener('click', function () {
      settings.imageUrl = '';
      applyCustomImage('');
      imageInput.value = '';
      // Also clear backend
      fetch('/api/mascot/reset', { method: 'POST' }).catch(function () {});
      saveSettings();
    });
  }

  function uploadMascotImage(file) {
    var formData = new FormData();
    formData.append('image', file);
    fetch('/api/mascot/upload', { method: 'POST', body: formData })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.url) {
          settings.imageUrl = data.url;
          applyCustomImage(data.url);
          saveSettings();
        } else if (data.error) {
          showToast(data.error, 'error');
        }
      })
      .catch(function () {
        // Keep the data URL as fallback if upload fails
        showToast('角色图片上传失败，仅本地生效', 'error');
      });
  }

  function applySettings() {
    el.style.display = settings.visible ? '' : 'none';
    document.getElementById('mpVisible').checked = settings.visible;
    document.getElementById('mpSpeech').checked = settings.speechEnabled;
    document.getElementById('mpSpeechFreq').value = settings.speechFreqMin;
    var freqLabel = document.getElementById('mpFreqLabel');
    if (freqLabel) freqLabel.textContent = settings.speechFreqMin + 's';
    document.getElementById('mpIdleAnim').checked = settings.idleAnim;

    if (!settings.speechEnabled) {
      clearTimeout(bubbleTimer);
      hideBubble();
    } else if (!bubbleTimer) {
      scheduleBubble();
    }
  }

  function endDrag() {
    if (!dragging) return;
    dragging = false;
    el.classList.remove('dragging');
    pos.x = target.x;
    pos.y = target.y;
    saveSettings();
  }

  function clampTarget() {
    var w = el.offsetWidth, h = el.offsetHeight;
    target.x = Math.max(0, Math.min(window.innerWidth - w, target.x));
    target.y = Math.max(0, Math.min(window.innerHeight - h, target.y));
  }

  function loop() {
    if (!dragging) {
      pos.x += (target.x - pos.x) * 0.08;
      pos.y += (target.y - pos.y) * 0.08;
    } else {
      pos.x = target.x;
      pos.y = target.y;
    }

    el.style.left = pos.x + 'px';
    el.style.top = pos.y + 'px';

    updateEyes();

    // Idle float (controllable)
    idleTime += 16;
    if (settings.idleAnim && idleTime > 3000) {
      var floatX = Math.sin(Date.now() / 2000) * 4;
      var floatY = Math.cos(Date.now() / 2400) * 3;
      target.x = pos.x + floatX;
      target.y = pos.y + floatY;
    }

    animId = requestAnimationFrame(loop);
  }

  function updateEyes() {
    var pupils = el.querySelectorAll('.mascot-pupil');
    if (!pupils.length) return;

    var rect = el.getBoundingClientRect();
    var cx = rect.left + rect.width / 2;
    var cy = rect.top + rect.height * 0.35;

    var dx = mouse.x - cx;
    var dy = mouse.y - cy;
    var dist = Math.sqrt(dx * dx + dy * dy);
    var maxDist = 5;
    var ex = dist > 0 ? (dx / dist) * Math.min(dist * 0.04, maxDist) : 0;
    var ey = dist > 0 ? (dy / dist) * Math.min(dist * 0.04, maxDist) : 0;

    pupils[0].style.transform = 'translate(' + ex + 'px,' + ey + 'px)';
    pupils[1].style.transform = 'translate(' + ex + 'px,' + ey + 'px)';
  }

  function showBubble(msg) {
    if (!settings.speechEnabled) return;
    bubble.textContent = msg;
    bubble.classList.add('show');
    clearTimeout(bubbleTimer);
    bubbleTimer = setTimeout(hideBubble, 3500);
  }

  function hideBubble() {
    bubble.classList.remove('show');
  }

  function scheduleBubble() {
    if (!settings.speechEnabled) {
      bubbleTimer = null;
      return;
    }
    var delay = settings.speechFreqMin * 1000 + Math.random() * (settings.speechFreqMax - settings.speechFreqMin) * 1000;
    bubbleTimer = setTimeout(function () {
      if (!dragging && idleTime > 4000) {
        var msg = MESSAGES[Math.floor(Math.random() * MESSAGES.length)];
        showBubble(msg);
      }
      scheduleBubble();
    }, delay);
  }

  function togglePanel() {
    panel.classList.toggle('show');
  }

  function hidePanel() {
    panel.classList.remove('show');
  }

  // Sync server preferences with localStorage (server wins for non-position keys)
  if (window.__MASCOT_CONFIG__) {
    loadSettings();
    var cfg = window.__MASCOT_CONFIG__;
    if (cfg.mascotImage) settings.imageUrl = cfg.mascotImage;
    if (cfg.preferences && Object.keys(cfg.preferences).length > 0) {
      var p = cfg.preferences;
      if (typeof p.mascot_visible === 'boolean') settings.visible = p.mascot_visible;
      if (typeof p.mascot_speech === 'boolean') settings.speechEnabled = p.mascot_speech;
      if (typeof p.mascot_speech_freq === 'number') {
        settings.speechFreqMin = p.mascot_speech_freq;
        settings.speechFreqMax = p.mascot_speech_freq + 5;
      }
      if (typeof p.mascot_idle_anim === 'boolean') settings.idleAnim = p.mascot_idle_anim;
    }
    saveSettings();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
