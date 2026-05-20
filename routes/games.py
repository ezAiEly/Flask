from flask import Blueprint, render_template, request, session, abort, jsonify
from models import db, Game

game_bp = Blueprint('game', __name__)

GAME_CATEGORIES = ['动作', '益智', '射击', '冒险', '策略', '休闲', '体育', '综合', '棋牌', '双人']
GAME_CATEGORY_ICONS = {
    '动作': 'fa-fist-raised', '益智': 'fa-puzzle-piece', '射击': 'fa-crosshairs',
    '冒险': 'fa-mountain', '策略': 'fa-chess', '休闲': 'fa-coffee',
    '体育': 'fa-futbol', '综合': 'fa-th-large', '棋牌': 'fa-chess-board',
    '双人': 'fa-user-friends',
}
GAME_CATEGORY_COLORS = {
    '动作': '#f5222d', '益智': '#722ed1', '射击': '#fa8c16',
    '冒险': '#52c41a', '策略': '#1890ff', '休闲': '#13c2c2',
    '体育': '#eb2f96', '综合': '#6366f1', '棋牌': '#a855f7',
    '双人': '#14b8a6',
}


@game_bp.route('/games')
def game_index():
    cat = request.args.get('category', '')
    sort = request.args.get('sort', 'hot')
    page = request.args.get('page', 1, type=int)
    per_page = 24
    offset = (page - 1) * per_page

    base = Game.query
    if cat and cat in GAME_CATEGORIES:
        base = base.filter_by(category=cat)

    if sort == 'new':
        base = base.order_by(Game.created_at.desc())
    else:
        base = base.order_by(Game.play_count.desc())

    total = base.count()
    games = base.offset(offset).limit(per_page + 1).all()
    has_more = len(games) > per_page
    games = games[:per_page]

    # Category counts for tabs
    cat_counts = {}
    for c in GAME_CATEGORIES:
        cat_counts[c] = Game.query.filter_by(category=c).count()

    return render_template('games.html',
        games=games, categories=GAME_CATEGORIES, category_icons=GAME_CATEGORY_ICONS,
        category_colors=GAME_CATEGORY_COLORS, cat_counts=cat_counts,
        current_cat=cat, current_sort=sort, page=page, has_more=has_more, total=total)


@game_bp.route('/game/<int:game_id>')
def game_play(game_id):
    game = db.session.get(Game, game_id)
    if game is None:
        abort(404)
    game.play_count += 1
    db.session.commit()

    # Related games (same category)
    related = Game.query.filter(
        Game.category == game.category, Game.id != game.id
    ).order_by(Game.play_count.desc()).limit(6).all()

    return render_template('game_play.html', game=game, related=related,
        category_icons=GAME_CATEGORY_ICONS, category_colors=GAME_CATEGORY_COLORS)


@game_bp.route('/games/category/<category_name>')
def game_category(category_name):
    if category_name not in GAME_CATEGORIES:
        abort(404)
    page = request.args.get('page', 1, type=int)
    per_page = 24
    offset = (page - 1) * per_page

    base = Game.query.filter_by(category=category_name).order_by(Game.play_count.desc())
    total = base.count()
    games = base.offset(offset).limit(per_page + 1).all()
    has_more = len(games) > per_page
    games = games[:per_page]

    return render_template('game_category.html',
        category_name=category_name, games=games, page=page,
        has_more=has_more, total=total,
        category_icon=GAME_CATEGORY_ICONS.get(category_name, 'fa-gamepad'),
        category_color=GAME_CATEGORY_COLORS.get(category_name, '#6366f1'))


# ── API ─────────────────────────────────────────────────

def _serialize_game(g):
    return {
        'id': g.id,
        'title': g.title,
        'description': g.description,
        'category': g.category,
        'cover_image': g.cover_image,
        'embed_url': g.embed_url,
        'play_count': g.play_count,
        'is_external': g.is_external,
        'created_at': g.created_at.isoformat(),
    }


@game_bp.route('/api/games')
def api_games():
    cat = request.args.get('category', '')
    sort = request.args.get('sort', 'hot')
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 24, type=int), 50)
    offset = (page - 1) * limit

    base = Game.query
    if cat and cat in GAME_CATEGORIES:
        base = base.filter_by(category=cat)
    if sort == 'new':
        base = base.order_by(Game.created_at.desc())
    else:
        base = base.order_by(Game.play_count.desc())

    total = base.count()
    items = base.offset(offset).limit(limit + 1).all()
    has_more = len(items) > limit
    items = items[:limit]

    return jsonify({
        'games': [_serialize_game(g) for g in items],
        'page': page, 'total': total, 'has_more': has_more,
    })


@game_bp.route('/api/games/hot')
def api_games_hot():
    limit = min(request.args.get('limit', 12, type=int), 30)
    games = Game.query.order_by(Game.play_count.desc()).limit(limit).all()
    return jsonify({'games': [_serialize_game(g) for g in games]})


@game_bp.route('/api/games/categories')
def api_games_categories():
    return jsonify({
        cat: {
            'count': Game.query.filter_by(category=cat).count(),
            'icon': GAME_CATEGORY_ICONS.get(cat, 'fa-gamepad'),
            'color': GAME_CATEGORY_COLORS.get(cat, '#6366f1'),
        }
        for cat in GAME_CATEGORIES
    })
