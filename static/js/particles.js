/**
 * Mouse particle trail — canvas-based cursor particles
 * Theme-aware, respects reduce-motion, toggleable via settings
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'particles_enabled';
  var enabled = true;

  // Check localStorage
  try {
    var saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== null) enabled = saved === 'true';
  } catch(e) {}

  // Check reduce-motion
  if (document.documentElement.classList.contains('reduce-motion')) enabled = false;

  var canvas = null;
  var ctx = null;
  var particles = [];
  var mouse = { x: -100, y: -100 };
  var animId = null;
  var lastSpawn = 0;
  var SPAWN_INTERVAL = 30; // ms between particle spawns
  var MAX_PARTICLES = 60;
  var PARTICLE_LIFE = 1200; // ms

  function getPrimaryColor() {
    var style = getComputedStyle(document.documentElement);
    return style.getPropertyValue('--primary-color').trim() || '#00a1d6';
  }

  function hexToRgb(hex) {
    var r = parseInt(hex.slice(1,3), 16);
    var g = parseInt(hex.slice(3,5), 16);
    var b = parseInt(hex.slice(5,7), 16);
    return { r: r, g: g, b: b };
  }

  function createParticle() {
    var color = hexToRgb(getPrimaryColor());
    var angle = Math.random() * Math.PI * 2;
    var speed = 0.3 + Math.random() * 1.2;
    return {
      x: mouse.x,
      y: mouse.y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      radius: 1.5 + Math.random() * 2.5,
      life: PARTICLE_LIFE,
      born: performance.now(),
      r: color.r,
      g: color.g,
      b: color.b
    };
  }

  function init() {
    canvas = document.createElement('canvas');
    canvas.className = 'particle-canvas';
    canvas.setAttribute('aria-hidden', 'true');
    canvas.style.cssText =
      'position:fixed;inset:0;z-index:1000;pointer-events:none;';
    document.body.appendChild(canvas);

    ctx = canvas.getContext('2d');
    resize();
    window.addEventListener('resize', resize);

    document.addEventListener('mousemove', function (e) {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    });

    // Expose toggle for settings page
    window.toggleParticles = function (on) {
      enabled = on;
      localStorage.setItem(STORAGE_KEY, on ? 'true' : 'false');
      if (on) {
        canvas.style.display = '';
        if (!animId) loop();
      } else {
        canvas.style.display = 'none';
        particles = [];
      }
    };

    if (enabled) loop();
  }

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  function loop() {
    if (!enabled) { animId = null; return; }
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    var now = performance.now();

    // Spawn new particles
    if (now - lastSpawn > SPAWN_INTERVAL && particles.length < MAX_PARTICLES) {
      particles.push(createParticle());
      lastSpawn = now;
    }

    // Update and draw
    for (var i = particles.length - 1; i >= 0; i--) {
      var p = particles[i];
      var elapsed = now - p.born;
      var progress = elapsed / p.life;

      if (progress >= 1) {
        particles.splice(i, 1);
        continue;
      }

      p.x += p.vx;
      p.y += p.vy;
      var alpha = 1 - progress;
      var radius = p.radius * (1 - progress * 0.5);

      ctx.beginPath();
      ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(' + p.r + ',' + p.g + ',' + p.b + ',' + (alpha * 0.6) + ')';
      ctx.fill();
    }

    animId = requestAnimationFrame(loop);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    if (document.body) init();
    else document.addEventListener('DOMContentLoaded', init);
  }
})();
