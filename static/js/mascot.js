/**
 * 看板娘 — 2D chibi mascot with mouse tracking, idle animation, speech bubbles
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

  var el = null, bubble = null;
  var pos = { x: 0, y: 0 };      // current position (center)
  var target = { x: 0, y: 0 };   // target position (drag destination)
  var dragging = false;
  var dragOff = { x: 0, y: 0 };
  var mouse = { x: 0, y: 0 };
  var animId = null;
  var bubbleTimer = null;
  var idleTime = 0;

  function init() {
    pos.x = window.innerWidth - 90;
    pos.y = window.innerHeight - 140;
    target.x = pos.x;
    target.y = pos.y;

    buildDOM();
    bindEvents();
    loop();
    scheduleBubble();
  }

  function buildDOM() {
    // Container
    el = document.createElement('div');
    el.className = 'mascot';
    el.style.cssText = 'left:' + pos.x + 'px;top:' + pos.y + 'px;';
    el.innerHTML =
      // Body
      '<div class="mascot-body">' +
        // Hair
        '<div class="mascot-hair"></div>' +
        '<div class="mascot-hair-back"></div>' +
        // Face
        '<div class="mascot-face">' +
          // Eyes
          '<div class="mascot-eye mascot-eye-left">' +
            '<div class="mascot-pupil"></div>' +
          '</div>' +
          '<div class="mascot-eye mascot-eye-right">' +
            '<div class="mascot-pupil"></div>' +
          '</div>' +
          // Blush
          '<div class="mascot-blush mascot-blush-left"></div>' +
          '<div class="mascot-blush mascot-blush-right"></div>' +
          // Mouth
          '<div class="mascot-mouth"></div>' +
        '</div>' +
        // Arms
        '<div class="mascot-arm mascot-arm-left"></div>' +
        '<div class="mascot-arm mascot-arm-right"></div>' +
      '</div>';

    // Speech bubble
    bubble = document.createElement('div');
    bubble.className = 'mascot-bubble';
    bubble.textContent = '你好呀~';
    el.appendChild(bubble);

    // Tooltip for close hint
    var tip = document.createElement('div');
    tip.className = 'mascot-tip';
    tip.textContent = '拖拽可移动 · 点击可切换表情';
    el.appendChild(tip);

    document.body.appendChild(el);
  }

  function bindEvents() {
    // Mouse tracking
    document.addEventListener('mousemove', function (e) {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      idleTime = 0;
    });

    // Drag
    el.addEventListener('mousedown', function (e) {
      if (e.button !== 0) return;
      dragging = true;
      var rect = el.getBoundingClientRect();
      dragOff.x = e.clientX - rect.left - rect.width / 2;
      dragOff.y = e.clientY - rect.top - rect.height / 2;
      el.classList.add('dragging');
      hideBubble();
    });

    // Touch drag
    el.addEventListener('touchstart', function (e) {
      dragging = true;
      var rect = el.getBoundingClientRect();
      dragOff.x = e.touches[0].clientX - rect.left - rect.width / 2;
      dragOff.y = e.touches[0].clientY - rect.top - rect.height / 2;
      el.classList.add('dragging');
      hideBubble();
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

    // Click for expression toggle
    el.addEventListener('click', function (e) {
      if (dragging) return;
      el.classList.toggle('happy');
      setTimeout(function () { el.classList.remove('happy'); }, 1200);
      var msg = MESSAGES[Math.floor(Math.random() * MESSAGES.length)];
      showBubble(msg);
    });
  }

  function endDrag() {
    if (!dragging) return;
    dragging = false;
    el.classList.remove('dragging');
    pos.x = target.x;
    pos.y = target.y;
  }

  function clampTarget() {
    var w = el.offsetWidth, h = el.offsetHeight;
    target.x = Math.max(0, Math.min(window.innerWidth - w, target.x));
    target.y = Math.max(0, Math.min(window.innerHeight - h, target.y));
  }

  function loop() {
    // Smooth follow
    if (!dragging) {
      pos.x += (target.x - pos.x) * 0.08;
      pos.y += (target.y - pos.y) * 0.08;
    } else {
      pos.x = target.x;
      pos.y = target.y;
    }

    el.style.left = pos.x + 'px';
    el.style.top = pos.y + 'px';

    // Eye tracking
    updateEyes();

    // Idle: gentle float when mouse is still
    idleTime += 16;
    if (idleTime > 3000) {
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
    bubble.textContent = msg;
    bubble.classList.add('show');
    clearTimeout(bubbleTimer);
    bubbleTimer = setTimeout(hideBubble, 3500);
  }

  function hideBubble() {
    bubble.classList.remove('show');
  }

  function scheduleBubble() {
    var delay = 8000 + Math.random() * 12000;
    setTimeout(function () {
      if (!dragging && idleTime > 4000) {
        var msg = MESSAGES[Math.floor(Math.random() * MESSAGES.length)];
        showBubble(msg);
      }
      scheduleBubble();
    }, delay);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
