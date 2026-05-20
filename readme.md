# 视频社区网站

类 B 站风格的视频社区，基于 Flask + SQLite + SocketIO，支持弹幕、游戏中心、看板娘等。

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env              # 编辑 .env 修改 SECRET_KEY 和 JWT_SECRET_KEY
python app.py
```

访问 http://127.0.0.1:5000

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | Flask 3.x + Jinja2 服务端渲染 |
| 数据库 | SQLite + SQLAlchemy + Flask-Migrate |
| 认证 | Session + JWT (Flask-JWT-Extended) |
| 实时通信 | Flask-SocketIO |
| CSRF 防护 | Flask-WTF |
| 图片处理 | Pillow（验证 + 缩略图） |
| 视频播放 | video.js 8.10 |
| 弹幕渲染 | Canvas API 自定义引擎 |
| 轮播图 | Swiper.js 11 |
| 弹窗 | Micromodal.js |
| 通知 | Notyf 3 |
| 日期选择 | flatpickr 4 + 中文 locale |
| 图标 | Font Awesome 6.7 |
| 前端 | 原生 JavaScript（IIFE 模式） + CSS Variables |
| 测试 | pytest |

## 项目结构

```
├── app.py                    # 应用工厂 create_app()
├── config.py                 # 配置类 + .env 加载
├── models.py                 # 数据模型（10 表 + 推荐引擎）
├── events.py                 # SocketIO 事件（弹幕实时推送）
├── requirements.txt
├── .env.example
├── routes/
│   ├── __init__.py           # 注册所有 Blueprint
│   ├── auth.py               # 注册 / 登录 / 登出
│   ├── main.py               # 首页 / 关于 / 联系 / 个人资料 / 头像 / 用户空间 / 动态 / 历史 / 设置
│   ├── video.py              # 视频 CRUD / 搜索 / 分类 / 弹幕 API / 评论 API / 互动 API
│   ├── social.py             # 关注 / 取关
│   └── games.py              # 游戏中心 / 游戏播放 / 分类浏览
├── tests/
│   ├── conftest.py           # pytest fixtures
│   └── test_routes.py        # 10 个冒烟测试
├── migrations/               # Flask-Migrate 迁移
├── static/
│   ├── css/
│   │   └── style.css         # 完整主题系统（CSS Variables + 深色模式）
│   ├── js/
│   │   ├── danmaku.js        # Canvas 弹幕引擎
│   │   ├── interaction.js    # 互动栏（点赞/投币/收藏/分享）
│   │   ├── home.js           # 首页 Tab + 轮播图 + 无限分页
│   │   ├── mascot.js         # 看板娘（拖拽/跟随/气泡/自定义导入）
│   │   └── particles.js      # 鼠标粒子尾迹
│   ├── games/                # 小游戏（2048 / 贪吃蛇 / 俄罗斯方块）
│   ├── avatars/              # 用户头像
│   ├── images/               # 系统图片库
│   ├── mascots/              # 自定义看板娘图片
│   └── videos/               # 视频文件（不纳入版本控制）
└── templates/
    ├── base.html             # 基础布局（导航栏 + 侧边栏 + 页脚）
    ├── index.html            # 首页（轮播图 + 推荐/热门 Tab）
    ├── video.html            # 播放页（弹幕 + 互动栏 + 评论区）
    ├── search.html           # 搜索结果
    ├── category.html         # 分类浏览
    ├── user_space.html       # 用户空间
    ├── upload_video.html     # 视频投稿
    ├── profile.html          # 个人资料 + 改密
    ├── settings.html         # 站点设置（强调色/字体/动画/看板娘）
    ├── login.html / register.html
    ├── history.html          # 观看历史
    ├── my_feed.html          # 关注动态
    ├── games.html            # 游戏中心
    ├── game_play.html        # 游戏播放页
    ├── game_category.html    # 游戏分类
    ├── about.html / contact.html
    ├── choose_avatar.html / upload_avatar.html
    └── error.html            # 错误页面
```

## 功能清单

### 用户系统
- 注册 / 登录（Session + JWT 双认证，JWT 过期自动跳转）
- 个人资料（头像上传 + 图片库选择 + 修改密码）
- 用户等级（Lv0-Lv6，基于上传/点赞/评论/观看量自动计算）
- 用户空间（投稿列表 + 动态时间线）
- 关注 / 取关 + 关注动态推送

### 视频系统
- 视频上传（最大 20GB，支持 mp4/webm/mkv/avi/mov/flv）
- 视频播放（video.js，多倍速 0.5x-2x）
- 封面图（上传封面 + ffmpeg 自动截帧回退）
- 标签系统（逗号分隔，个性化推荐依据）
- 8 个分类：动画 / 音乐 / 游戏 / 知识 / 科技 / 生活 / 时尚 / 娱乐
- 搜索（标题 + 描述模糊匹配）
- JSON-LD 结构化数据（SEO）

### 弹幕系统
- Canvas 渲染引擎，3 种模式（滚动/顶部/底部）
- 8 色可选，实时 WebSocket 推送
- 自定义颜色 + 轨道碰撞避免

### 评论区
- 发表评论 + 回复（1 层嵌套）
- 最新/最热排序，分页加载
- 点赞切换

### 互动栏
- 点赞 / 投币 / 收藏 / 分享
- 投币数选择弹窗

### 游戏中心（10 个分类）
- 动作 / 益智 / 射击 / 冒险 / 策略 / 休闲 / 体育 / 综合 / 棋牌 / 双人
- 3 款自带小游戏（2048 / 贪吃蛇 / 俄罗斯方块）
- iframe 嵌入外部游戏 + 全屏播放
- 分类浏览 + 排序（最热/最新）

### 推荐引擎
```
热度 = 播放量×1 + 点赞数×2 + 收藏数×3 + 硬币数×5
```
- `GET /api/videos/recommend` — 基于观看历史标签的个性化推荐
- `GET /api/videos/hot` — 全站热门排行（分页）

### 主题与自定义
- 3 态主题切换（浅色/深色/跟随系统），FOUC 防闪烁
- 强调色自定义（6 预设 + 取色器，实时预览）
- 字体大小（小/中/大）
- 减少动画选项
- 侧边栏折叠状态记忆

### 看板娘
- 纯 CSS 绘制 2D 角色（可替换为自定义图片）
- 眼睛跟随鼠标、拖拽移动、待机浮动动画
- 随机气泡消息（频率可调）
- 设置面板（显示/气泡/动画开关）
- 位置自动保存

### 鼠标粒子尾迹
- Canvas 粒子系统，跟随鼠标
- 颜色跟随强调色，渐隐消失
- 支持开关 + 减少动画时自动禁用

### 页面增强
- 滚动进度条 + 回到顶部按钮
- 首页视频轮播图（Swiper.js，自动播放）
- 可访问弹窗（Micromodal，替换 confirm）
- Toast 通知（Notyf，3 种类型）
- 响应式布局（适配手机端）

## 推荐引擎 API

| 端点 | 说明 |
|---|---|
| `GET /api/videos/recommend?page=1&limit=12` | 个性化推荐 |
| `GET /api/videos/hot?page=1&limit=12` | 全站热门 |
| `GET /api/videos/search?q=关键词` | 搜索建议 |

## 常用命令

```bash
# 运行
python app.py

# 数据库迁移
flask db migrate -m "描述"
flask db upgrade

# 测试
python -m pytest tests/ -v
```

## 设计主题

| 变量 | 浅色 | 深色 |
|---|---|---|
| `--primary-color` | `#00a1d6` | `#00b8e6` |
| `--bg-color` | `#f4f5f7` | `#0f1218` |
| `--card-bg` | `#fff` | `#1a1e27` |
| `--text-color` | `#18191c` | `#e0e0e0` |
| `--border-color` | `#e3e5e7` | `#2a3040` |

用户可在 `/settings` 自定义强调色，偏好持久化到数据库。
