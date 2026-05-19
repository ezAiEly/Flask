/**
 * DanmakuEngine — B站风格弹幕渲染引擎
 * 依赖：SocketIO client (io)、<canvas>、<video>
 */
(function () {
  'use strict';

  var D = {
    MAX_ACTIVE: 30,           // 同屏最多弹幕数
    SCROLL_SPEED: 140,        // 滚动速度 px/s
    TRACK_HEIGHT: 30,         // 每条滚动轨道高度
    FONT_SIZE: 22,
    FONT: 'bold 22px "Microsoft YaHei","PingFang SC",sans-serif',
    STROKE_COLOR: 'rgba(0,0,0,0.65)',
    STROKE_WIDTH: 2,
    TOP_DURATION: 5000,       // 顶部/底部弹幕停留 ms
    GAP_BETWEEN: 30,          // 同轨道两条弹幕最小间距 px
  };

  function DanmakuEngine(opts) {
    this.video = opts.video;
    this.videoId = opts.videoId;
    this.jwtToken = opts.jwtToken || '';

    // Canvas 由外部注入或自行创建
    this.canvas = opts.canvas || this._createCanvas();
    this.ctx = this.canvas.getContext('2d');

    this.pool = [];            // 全部弹幕 {id,content,color,mode,play_time,username,...}
    this.active = [];          // 当前屏幕上的弹幕
    this.tracks = [];          // 轨道占位: 每条轨道当前最右端 x 坐标
    this.trackCount = 10;
    this.lastTime = 0;         // 上次检查的时间点
    this.animId = null;
    this.prevTs = 0;
    this.paused = false;

    // 发送面板状态
    this.sendColor = '#FFFFFF';
    this.sendMode = 'scroll';

    this._bindVideo();
    this._loadPool();
    this._connect();
    this._loop();
  }

  // ── 创建 Canvas ──
  DanmakuEngine.prototype._createCanvas = function () {
    var container = document.querySelector('.video-js');
    if (!container) throw new Error('video.js container not found');
    container.style.position = 'relative';
    var c = document.createElement('canvas');
    c.className = 'danmaku-canvas';
    container.appendChild(c);
    return c;
  };

  // ── Canvas 尺寸同步 ──
  DanmakuEngine.prototype._resize = function () {
    var container = this.canvas.parentElement;
    if (!container) return;
    var cr = container.getBoundingClientRect();
    var vr = this.video.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;

    this.canvas.width = cr.width * dpr;
    this.canvas.height = cr.height * dpr;
    this.canvas.style.width = cr.width + 'px';
    this.canvas.style.height = cr.height + 'px';
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    this.drawX = vr.left - cr.left;
    this.drawY = vr.top - cr.top;
    this.drawW = vr.width;
    this.drawH = vr.height;

    this.trackCount = Math.max(Math.floor(this.drawH / D.TRACK_HEIGHT), 8);
    this.tracks = new Array(this.trackCount);
    for (var i = 0; i < this.trackCount; i++) this.tracks[i] = -Infinity;
  };

  // ── 视频事件绑定 ──
  DanmakuEngine.prototype._bindVideo = function () {
    var self = this;
    this._resize();
    window.addEventListener('resize', function () { self._resize(); });
    if (window.ResizeObserver) {
      new ResizeObserver(function () { self._resize(); }).observe(this.video);
    }

    this.video.addEventListener('play', function () { self.paused = false; self.prevTs = 0; });
    this.video.addEventListener('pause', function () { self.paused = true; });
    this.video.addEventListener('seeked', function () {
      // 清屏，重置时间线
      self.active = [];
      for (var i = 0; i < self.trackCount; i++) self.tracks[i] = -Infinity;
      self.lastTime = self.video.currentTime;
      // 清除激活标记以便重新加载
      for (var j = 0; j < self.pool.length; j++) self.pool[j]._used = false;
    });
  };

  // ── 载入历史弹幕 ──
  DanmakuEngine.prototype._loadPool = function () {
    var self = this;
    fetch('/api/videos/' + this.videoId + '/danmakus')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        self.pool = data.danmakus.sort(function (a, b) { return a.play_time - b.play_time; });
      })
      .catch(function (e) { console.error('Load danmakus failed:', e); });
  };

  // ── SocketIO 连接 ──
  DanmakuEngine.prototype._connect = function () {
    var self = this;
    var opts = { transports: ['websocket', 'polling'] };
    if (this.jwtToken) opts.extraHeaders = { Authorization: 'Bearer ' + this.jwtToken };
    this.socket = io(opts);
    this.socket.emit('join', { video_id: this.videoId });
    this.socket.on('new_danmaku', function (d) {
      self.pool.push(d);
      // 时间窗口内则立即显示
      var ct = self.video.currentTime;
      if (d.play_time >= ct - 1 && d.play_time <= ct + 0.5) {
        self._activate(d);
      }
    });
  };

  // ── 主循环 ──
  DanmakuEngine.prototype._loop = function () {
    var self = this;
    var frame = function (ts) {
      if (self.prevTs && !self.paused) {
        var dt = (ts - self.prevTs) / 1000;
        if (dt > 0 && dt < 1) {  // 忽略异常帧
          self._tick(dt);
        }
      }
      self.prevTs = ts;
      self._draw();
      self.animId = requestAnimationFrame(frame);
    };
    this.animId = requestAnimationFrame(frame);
  };

  // ── 每帧逻辑 ──
  DanmakuEngine.prototype._tick = function (dt) {
    var ct = this.video.currentTime;
    if (isNaN(ct)) return;

    // 初始化 lastTime
    if (this.lastTime === 0) { this.lastTime = ct; return; }

    // 跳变过大（暂停后恢复、切后台等）忽略累积弹幕
    if (ct - this.lastTime > 2 || ct < this.lastTime) {
      this.lastTime = ct;
      return;
    }

    // 取出时间段内应出现的弹幕
    for (var i = 0; i < this.pool.length; i++) {
      var d = this.pool[i];
      if (d._used) continue;
      if (d.play_time >= this.lastTime && d.play_time <= ct) {
        this._activate(d);
      }
    }
    this.lastTime = ct;

    // 更新位置
    for (var j = this.active.length - 1; j >= 0; j--) {
      var a = this.active[j];
      if (a.mode === 'scroll') {
        a.x -= D.SCROLL_SPEED * dt;
        this.tracks[a.trackIdx] = a.x + a.width;
      }
    }
  };

  // ── 绘制 ──
  DanmakuEngine.prototype._draw = function () {
    var ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width / (window.devicePixelRatio || 1), this.canvas.height / (window.devicePixelRatio || 1));
    ctx.font = D.FONT;
    ctx.textBaseline = 'middle';

    // 裁剪到视频区域（避免画到控制栏）
    ctx.save();
    ctx.beginPath();
    ctx.rect(this.drawX, this.drawY, this.drawW, this.drawH);
    ctx.clip();

    var now = performance.now();
    for (var i = this.active.length - 1; i >= 0; i--) {
      var d = this.active[i];
      var remove = false;

      if (d.mode === 'scroll') {
        if (d.x + d.width < this.drawX) {
          this.tracks[d.trackIdx] = -Infinity;
          remove = true;
        }
      } else {
        if (now - d.born >= D.TOP_DURATION) {
          remove = true;
        }
      }

      if (remove) {
        this.active.splice(i, 1);
        continue;
      }

      // 描边 + 填充
      ctx.strokeStyle = D.STROKE_COLOR;
      ctx.lineWidth = D.STROKE_WIDTH;
      ctx.lineJoin = 'round';
      ctx.strokeText(d.content, d.x, d.y);
      ctx.fillStyle = d.color;
      ctx.fillText(d.content, d.x, d.y);
    }

    ctx.restore();
  };

  // ── 激活弹幕（分配轨道） ──
  DanmakuEngine.prototype._activate = function (d) {
    d._used = true;
    if (this.active.length >= D.MAX_ACTIVE) return;

    this.ctx.font = D.FONT;
    var tw = this.ctx.measureText(d.content).width;

    var y;
    if (d.mode === 'scroll') {
      var track = -1;
      for (var i = 0; i < this.trackCount; i++) {
        if (this.tracks[i] <= this.drawX + this.drawW - tw - D.GAP_BETWEEN) {
          track = i; break;
        }
      }
      if (track === -1) { d._used = false; return; } // 无可用轨道，丢弃
      y = this.drawY + track * D.TRACK_HEIGHT + D.TRACK_HEIGHT * 0.75;
      this.active.push({
        id: d.id, content: d.content, color: d.color, mode: 'scroll',
        x: this.drawX + this.drawW,
        y: y, width: tw, trackIdx: track, born: performance.now()
      });
      this.tracks[track] = this.drawX + this.drawW + tw;
    } else if (d.mode === 'top') {
      y = this.drawY + D.TRACK_HEIGHT * 0.75;
      // 避让已存在的顶部弹幕
      var topCount = 0;
      for (var k = 0; k < this.active.length; k++) {
        if (this.active[k].mode === 'top') topCount++;
      }
      if (topCount >= 3) { d._used = false; return; }
      this.active.push({
        id: d.id, content: d.content, color: d.color, mode: 'top',
        x: this.drawX + (this.drawW - tw) / 2,
        y: y + topCount * D.TRACK_HEIGHT,
        width: tw, born: performance.now()
      });
    } else { // bottom
      var botCount = 0;
      for (var m = 0; m < this.active.length; m++) {
        if (this.active[m].mode === 'bottom') botCount++;
      }
      if (botCount >= 3) { d._used = false; return; }
      this.active.push({
        id: d.id, content: d.content, color: d.color, mode: 'bottom',
        x: this.drawX + (this.drawW - tw) / 2,
        y: this.drawY + this.drawH - D.TRACK_HEIGHT * (botCount + 0.5),
        width: tw, born: performance.now()
      });
    }
  };

  // ── 发送弹幕 ──
  DanmakuEngine.prototype.send = function (content) {
    content = (content || '').trim();
    if (!content) return;
    this.socket.emit('send_danmaku', {
      video_id: this.videoId,
      content: content,
      play_time: this.video.currentTime,
      color: this.sendColor,
      mode: this.sendMode
    });
  };

  // ── 销毁 ──
  DanmakuEngine.prototype.destroy = function () {
    if (this.animId) cancelAnimationFrame(this.animId);
    if (this.socket) this.socket.disconnect();
  };

  window.DanmakuEngine = DanmakuEngine;
})();
