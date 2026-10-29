"""
config.py — Application configuration for SafeRoad.

All environment-specific settings live here so the rest of the
application remains configuration-agnostic.
"""

import os

# Absolute path of the directory that contains this file.
basedir = os.path.abspath(os.path.dirname(__file__))

# Lightweight .env loader (zero external dependencies)
_env_file = os.path.join(basedir, '.env')
if os.path.isfile(_env_file):
    try:
        with open(_env_file, 'r', encoding='utf-8') as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
    except Exception:
        pass


class Config:
    # -----------------------------------------------------------------
    # Security
    # -----------------------------------------------------------------
    SECRET_KEY = os.environ.get('SECRET_KEY', 'saferoad-secret-key-2026')

    # -----------------------------------------------------------------
    # Database
    # -----------------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(basedir, 'saferoad.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # -----------------------------------------------------------------
    # File uploads
    # -----------------------------------------------------------------
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024          # 16 MB hard limit
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # -----------------------------------------------------------------
    # Admin credentials (no Admin DB model — kept in config only)
    # -----------------------------------------------------------------
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'saferoad2026')

    # -----------------------------------------------------------------
    # Email Notification Configuration (Standard SMTP)
    # -----------------------------------------------------------------
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'usikarlavenkat@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'ogjnsrszdoskcnnn')
    MAIL_DEFAULT_SENDER = os.environ.get(
        'MAIL_DEFAULT_SENDER',
        'SafeRoad Hyderabad <usikarlavenkat@gmail.com>'
    )
    MAIL_ENABLED = True

