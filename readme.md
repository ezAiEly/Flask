# Video Community Platform

A Bilibili-style video community platform built with Flask + SQLAlchemy + SocketIO. Features real-time danmaku, game center, Live2D mascot, SSR templates, and comprehensive Web API demos.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env              # Edit SECRET_KEY and JWT_SECRET_KEY
python app.py
```

Visit **http://127.0.0.1:5000**

### Run the second microservice (API Gateway Demo)

```bash
cd service2
python app.py   # Starts on port 8002
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask 3.x + Jinja2 (SSR) |
| Database | SQLAlchemy ORM + MySQL/SQLite + Flask-Migrate |
| Auth | Session + JWT (Flask-JWT-Extended) |
| Real-time | Flask-SocketIO (danmaku + live chat) |
| Security | Flask-WTF (CSRF), Flask-Limiter (rate limiting), HMAC-SHA256 (webhooks), server-side CAPTCHA |
| Image | Pillow (validation, watermark, compression, QR code) |
| Video | video.js 8.10 + Canvas danmaku engine |
| Carousel | Swiper.js 11 |
| Charts | ECharts 5.6 |
| Modals | Micromodal.js |
| Toasts | Notyf 3 |
| Icons | Font Awesome 6.7 |
| Frontend | Vanilla JS (IIFE) + CSS Variables + Dark Mode |
| Testing | pytest |

## Project Structure

```
├── app.py                       # App factory create_app()
├── config.py                    # Config classes + .env loading
├── models.py                    # 19 models + recommendation engine + XP system
├── events.py                    # SocketIO events (danmaku + live chat)
├── extensions.py                # Flask-Limiter instance
├── requirements.txt
├── .env / .env.example
├── routes/
│   ├── __init__.py              # Register all blueprints (10 total)
│   ├── auth.py                  # Register / Login / Logout / CAPTCHA / Password reset
│   ├── main.py                  # Home / About / Profile / Avatar / Settings / Stats API / Gateway
│   ├── video.py                 # Video CRUD / Search / Categories / Danmaku / Comments / Interactions
│   ├── social.py                # Follow / Unfollow / Profile API
│   ├── games.py                 # Game center / Play / Categories
│   ├── notifications.py         # Notification CRUD + unread count
│   ├── playlists.py             # Playlist CRUD + video add/remove
│   ├── admin.py                 # Admin dashboard (user / video management)
│   ├── third_party.py           # Weather API proxy
│   ├── qrcode.py                # QR code generator (server-side)
│   └── webhook.py               # Webhook receiver + HMAC verification + simulator
├── service2/
│   └── app.py                   # Standalone microservice on port 8002 (API Gateway demo)
├── utils/
│   ├── captcha_utils.py         # Server-side CAPTCHA image generation
│   └── image_utils.py           # Watermark + compression utilities
├── tests/
│   ├── conftest.py              # pytest fixtures (in-memory SQLite)
│   └── test_routes.py           # 10 smoke tests
├── migrations/                  # Flask-Migrate (Alembic)
├── static/
│   ├── css/
│   │   └── style.css            # ~3000 lines: theme system, dark mode, chat, admin, responsive
│   ├── js/
│   │   ├── danmaku.js           # Canvas danmaku engine (scroll/top/bottom, collision avoidance)
│   │   ├── interaction.js       # Like / Coin / Favorite / Share bar
│   │   ├── home.js              # Homepage tabs + carousel + infinite scroll
│   │   └── live2d-widget.js     # Live2D Cubism 2 model loader (9 characters)
│   ├── live2d/                  # Live2D SDK + 9 character models
│   ├── games/                   # Embedded HTML5 games (2048 / Snake / Tetris)
│   ├── avatars/                 # User avatars (watermarked & compressed)
│   ├── images/                  # System image library
│   ├── mascots/                 # Custom mascot images
│   ├── covers/                  # Video cover thumbnails
│   └── videos/                  # Video files (not in version control)
└── templates/
    ├── base.html                # Layout: navbar, sidebar (10 nav items), footer, chat widget, theme
    ├── index.html               # Home: hero carousel, category chips, recommend/hot tabs, infinite scroll
    ├── video.html               # Player: video.js, danmaku canvas, interaction bar, comments (nested)
    ├── search.html / category.html
    ├── login.html / register.html  # With CAPTCHA
    ├── profile.html             # User stats + ECharts pie/line charts + password change
    ├── user_space.html          # Public user space (videos + feed tabs, follow button)
    ├── upload_video.html        # Video upload with XHR progress bar
    ├── settings.html            # Theme, Live2D model, playback, accent color
    ├── history.html / my_feed.html
    ├── games.html / game_play.html / game_category.html
    ├── qrcode.html              # QR code generator (style, color, logo options)
    ├── gateway.html             # API Gateway demo (multi-service concurrent fetch)
    ├── webhook.html             # Webhook dashboard (log table + simulator)
    ├── admin/
    │   ├── dashboard.html       # Stats, recent users, recent videos
    │   ├── users.html           # User management (toggle admin)
    │   └── videos.html          # Video management (delete)
    ├── about.html / contact.html
    ├── choose_avatar.html / upload_avatar.html
    └── error.html
```

## Feature Checklist (Assignment Coverage)

### 1. User Auth & Personalization ✅
- Session + JWT dual authentication
- "Welcome back, username" banner after login
- Conditional rendering: unauthenticated users see login prompts
- Personal data: my videos, watch history, followers, XP/level
- Password change & reset (token-based, 1-hour expiry)
- **Server-side CAPTCHA** on login/register forms
- Admin role (`is_admin`): `/admin` restricted, delete buttons hidden from non-owners

### 2. Dynamic Data Interaction (DB CRUD) ✅
- Search: `/search?q=keyword` — title + description LIKE query, paginated JSON
- Comments: permanent storage, nested replies, newest/hottest sort, like toggling
- Pagination: all list endpoints, frontend Fetch API
- **ECharts dashboard** on profile page: pie chart (videos by category) + line chart (daily views, 30-day)
- **Infinite scroll** on homepage (IntersectionObserver auto-load)

### 3. Real-time Data / WebSocket ✅
- **Real-time danmaku**: Canvas engine, 3 modes, 8 colors, WebSocket broadcast via SocketIO
- **Live chat room**: collapsible widget, SocketIO `join_chat` / `send_message`, message history (200)
- **Real-time notifications**: push on follow/like/coin/comment/reply, unread count, mark read

### 4. File Upload & Processing ✅
- **Avatar upload**: PIL MIME validation, server-side watermark + compression
- **Video upload**: 6 formats, 20GB max, XHR upload progress bar, ffmpeg cover extraction
- **Video cover**: user upload + ffmpeg auto-thumbnail fallback

### 5. Background Tasks & Progress ✅
- **Upload progress bar**: XHR.upload.onprogress with percentage + file size display
- (Celery async queue documented in `Video_Community_Feature_Guide.docx`)

### 6. Third-party API Integration ✅
- **Weather API**: backend proxy at `/api/third/weather?city=` (OpenWeatherMap, API key in .env)
- **QR Code generator**: server-side rendering with `qrcode` library, logo/color/style options
- (Alipay sandbox integration documented in guide)

### 7. Security & Validation ✅
- **CAPTCHA**: server-generated image on login/register, session-verified
- **CSRF protection**: Flask-WTF on all form POSTs
- **XSS prevention**: Jinja2 auto-escaping + JS `escapeHtml()`
- **Rate limiting**: 300/day 60/hour global, stricter on auth endpoints
- **Password hashing**: Werkzeug scrypt
- **Image validation**: PIL file-header verification (prevents extension spoofing)
- **Admin permission**: `/admin` blocked for non-admin users

### 8. Server-Side Rendering (SSR) ✅
- Jinja2 templates render full HTML on server
- View Page Source shows actual content (username, video titles, categories) — not empty `<div id="root">`
- JSON-LD structured data for SEO (video + game pages)

### 9. Webhook / Callback ✅
- `POST /api/webhook/<event_type>` — universal webhook receiver
- HMAC-SHA256 signature verification (`X-Webhook-Signature` header)
- Handlers: `payment_completed` → coins, `video_ready` → notification, `user_updated`, `comment_moderated`
- `WebhookLog` model stores all events (valid + invalid)
- `/webhook-dashboard`: live log table + **webhook simulator** to send test events

### 10. Multi-backend / API Gateway ✅
- Main app (Flask, port 5000/8001) + Service 2 (Flask, port 8002)
- `/gateway-demo`: frontend fires 3 concurrent `fetch()` calls to different ports simultaneously
- `Promise.all()` merges results — demonstrates microservice aggregation
- Visible in browser Network tab: requests hitting different origins

### 11. Admin Dashboard ✅
- `/admin`: stats overview (users/videos/comments count)
- User management: list, paginate, toggle admin role
- Video management: list, paginate, delete any video

### 12. Charts & Data Visualization ✅
- ECharts pie chart: videos by category
- ECharts line chart: daily views trend (30 days, smooth area fill)
- Backend: `/api/stats/overview` returns aggregated JSON

### 13. Live2D Mascot ✅
- 9 Cubism 2 character models (Pio, Tia, 22, 33, Shizuku, Neptune, Noir, Murakumo)
- Model switching, size presets, left/right position
- Idle tip bubbles every 30s
- Settings persistence in user preferences

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/captcha` | GET | Generate CAPTCHA image (base64) |
| `/api/stats/overview` | GET | User statistics for ECharts |
| `/api/third/weather?city=` | GET | Weather proxy (OpenWeatherMap) |
| `/api/qrcode?text=&style=&logo=&fg=&bg=` | GET | Generate QR code PNG |
| `/api/webhook/<event_type>` | POST | Receive webhook (HMAC verified) |
| `/api/webhook/simulate` | POST | Simulate a webhook event |
| `/api/webhook/logs` | GET | Webhook log (JSON) |
| `/api/notifications` | GET | User notifications (paginated) |
| `/api/notifications/unread-count` | GET | Unread notification count |
| `/api/playlists` | GET/POST | List / Create playlists |
| `/api/playlists/<id>/videos` | GET/POST | List / Add playlist videos |
| `/api/videos/recommend` | GET | Personalized recommendations |
| `/api/videos/hot` | GET | Hot videos (popularity-ranked) |
| `/api/video/<id>/interactions` | GET | Like/coin/fav counts + user state |
| `/api/video/<id>/comments` | GET/POST | Comments with nested replies |
| `/api/video/<id>/progress` | GET/POST | Watch progress save/resume |
| `/api/video/<id>/report` | POST | Report video |
| `/api/feed` | GET | Followed users' activity feed |
| `/api/history/clear` | POST | Clear watch history |

## Commands

```bash
# Run
python app.py

# Service 2 (for API Gateway demo)
cd service2 && python app.py

# Database migration
flask db migrate -m "description"
flask db upgrade

# Tests
python -m pytest tests/ -v
```

## Design System

| Variable | Light | Dark |
|---|---|---|
| `--primary-color` | `#00a1d6` | `#00b8e6` |
| `--bg-color` | `#f4f5f7` | `#0f1218` |
| `--card-bg` | `#fff` | `#1a1e27` |
| `--text-color` | `#18191c` | `#e0e0e0` |
| `--border-color` | `#e3e5e7` | `#2a3040` |

3-state theme (light/dark/system), FOUC prevention, 6 accent color presets + custom picker, font size (S/M/L), reduce-motion support. Preferences persisted per-user in database.
