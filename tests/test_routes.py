def test_index_ok(client):
    resp = client.get('/')
    assert resp.status_code == 200


def test_about_ok(client):
    resp = client.get('/about')
    assert resp.status_code == 200


def test_contact_get_ok(client):
    resp = client.get('/contact')
    assert resp.status_code == 200


def test_login_page_ok(client):
    resp = client.get('/login-page')
    assert resp.status_code == 200


def test_register_page_ok(client):
    resp = client.get('/register-page')
    assert resp.status_code == 200


def test_register_api_creates_user(client):
    resp = client.post('/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': '123456'
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert 'access_token' in data


def test_login_api(client):
    # register first
    client.post('/register', json={
        'username': 'loginuser',
        'email': 'login@example.com',
        'password': 'pass123'
    })
    # then login via /login
    resp = client.post('/login', json={
        'username': 'loginuser',
        'password': 'pass123'
    })
    assert resp.status_code == 200
    assert 'access_token' in resp.get_json()


def test_video_page_404_for_missing(client):
    resp = client.get('/video/99999')
    assert resp.status_code == 404


def test_user_space_404_for_missing(client):
    resp = client.get('/user/nonexistent')
    assert resp.status_code == 404


def test_api_routes_return_json(client):
    # danmaku API for nonexistent video
    resp = client.get('/api/videos/1/danmakus')
    assert resp.status_code == 200
    assert 'danmakus' in resp.get_json()
