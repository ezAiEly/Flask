import os
import datetime
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-me-to-a-strong-secret')
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=1)

    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///users.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = 20 * 1024 * 1024 * 1024  # 20GB

    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'avatars')
    VIDEO_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'videos')

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    VIDEO_ALLOWED_EXTENSIONS = {'mp4', 'webm', 'mkv', 'avi', 'mov', 'flv'}

    WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
