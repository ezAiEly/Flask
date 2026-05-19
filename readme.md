# 视频社区网站

一个类 B 站风格的视频社区，基于 Flask + SQLite + SocketIO。

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env      # 编辑 .env 修改密钥
python app.py
```

访问 http://127.0.0.1:5000

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | Flask 3.x |
| 数据库 | SQLite + SQLAlchemy + Flask-Migrate |
| 认证 | Session + JWT (Flask-JWT-Extended) |
| 实时通信 | Flask-SocketIO + eventlet |
| 视频播放 | video.js |
| 弹幕渲染 | Canvas API |
| 前端 | Jinja2 + 原生 JavaScript + Font Awesome 6 |
| 样式 | 自定义 CSS（CSS Variables, Flex, Grid） |
| 测试 | pytest |

## 项目结构

```
├── app.py                  # 应用工厂 create_app()
├── config.py               # 配置类（开发/生产）+ .env 加载
├── models.py               # 7 个数据模型 + 工具函数
├── events.py               # SocketIO 事件处理（弹幕）
├── requirements.txt
├── .env                    # 环境变量（密钥等）
├── routes/
│   ├── __init__.py         # 注册所有 Blueprint
│   ├── auth.py             # 注册、登录、登出、改密
│   ├── main.py             # 首页、关于、联系、个人资料、头像、用户空间、动态
│   ├── video.py            # 视频上传/播放/删除、弹幕 API、互动 API
│   └── social.py           # 关注/取关
├── tests/
│   ├── conftest.py         # pytest fixtures（内存数据库）
│   └── test_routes.py      # 10 条冒烟测试
├── migrations/             # Flask-Migrate 迁移文件
├── static/
│   ├── css/style.css
│   ├── js/
│   │   ├── danmaku.js      # 弹幕引擎（Canvas）
│   │   └── interaction.js  # 互动栏（点赞/投币/收藏/分享）
│   ├── avatars/            # 用户头像
│   ├── images/             # 系统图片库
│   └── videos/             # 视频文件
└── templates/
    ├── base.html           # 基础布局
    ├── index.html          # 首页（视频流 + 分页）
    ├── video.html          # 播放页（弹幕 + 互动）
    ├── user_space.html     # 用户空间（投稿 + 动态）
    ├── upload_video.html   # 视频投稿
    ├── profile.html        # 个人资料 + 改密
    ├── login.html          # 登录
    ├── register.html       # 注册
    ├── about.html          # 关于
    ├── contact.html        # 联系我们
    ├── choose_avatar.html  # 选择头像
    ├── upload_avatar.html  # 上传头像
    └── error.html          # 错误页面
```

## 功能

- 用户注册/登录（Session + JWT 双认证）
- 视频上传（最大 20GB）、播放、删除
- 弹幕系统（滚动/顶部/底部，8 色可选，实时 WebSocket 推送）
- 视频互动（点赞、投币、收藏、分享）
- 关注/取关
- 动态推送（粉丝可见上传/点赞/投币/收藏）
- 用户空间（投稿列表 + 动态时间线）
- 头像管理（上传 + 图片库选择）
- 个人资料 + 修改密码
- 联系我们留言
- 响应式布局

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
