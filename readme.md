# Flask Web 应用

## 启动

```bash
pip install -r requirements.txt
python app.py
```

访问 http://127.0.0.1:5000

## 项目结构

```
├── app.py              # 主程序（路由、模型、配置）
├── requirements.txt    # Python 依赖
├── instance/
│   └── users.db        # SQLite 数据库（自动创建）
├── static/
│   ├── css/style.css   # 样式
│   ├── avatars/        # 用户上传的头像
│   └── images/         # 系统图片库
└── templates/
    ├── base.html       # 基础布局（导航、页脚）
    ├── index.html      # 首页
    ├── about.html      # 关于
    ├── contact.html    # 联系我们
    ├── login.html      # 登录
    ├── register.html   # 注册
    ├── profile.html    # 个人资料
    ├── choose_avatar.html  # 选择头像
    ├── upload_avatar.html  # 上传头像
    └── error.html      # 错误页面
```

## 功能

- 用户注册 / 登录（Session + JWT 双认证）
- 个人资料页面
- 头像上传与图片库选择
- 联系我们留言
- 响应式布局（适配移动端）
