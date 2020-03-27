import configparser
import os
import sys
from urllib.parse import urlparse

from django.utils.crypto import get_random_string

config = configparser.RawConfigParser()
if 'PRETRAX_CONFIG_FILE' in os.environ:
    config.read_file(
        open(
            os.environ.get('PRETRAX_CONFIG_FILE'),
            encoding='utf-8'))
else:
    config.read(['/etc/pretrax/pretrax.cfg',
                 os.path.expanduser('~/.pretrax.cfg'),
                 'pretrax.cfg'],
                encoding='utf-8')


CONFIG_FILE = config
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = config.get(
    'pretrax',
    'datadir',
    fallback=os.environ.get(
        'DATA_DIR',
        'data'))
LOG_DIR = os.path.join(DATA_DIR, 'logs')
MEDIA_ROOT = os.path.join(DATA_DIR, 'media')

if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)
if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)

if config.has_option('django', 'secret'):
    SECRET_KEY = config.get('django', 'secret')
else:
    SECRET_FILE = os.path.join(DATA_DIR, '.secret')
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, 'r') as f:
            SECRET_KEY = f.read().strip()
    else:
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        SECRET_KEY = get_random_string(50, chars)
        with open(SECRET_FILE, 'w') as f:
            os.chmod(SECRET_FILE, 0o600)
            try:
                os.chown(SECRET_FILE, os.getuid(), os.getgid())
            except AttributeError:
                pass  # os.chown is not available on Windows
            f.write(SECRET_KEY)


# Adjustable settings

debug_fallback = "runserver" in sys.argv
DEBUG = config.getboolean('django', 'debug', fallback=debug_fallback)

db_backend = config.get('database', 'backend', fallback='sqlite3')
if db_backend == 'postgresql_psycopg2':
    db_backend = 'postgresql'
DATABASE_IS_GALERA = config.getboolean('database', 'galera', fallback=False)
if DATABASE_IS_GALERA and 'mysql' in db_backend:
    db_options = {
        'init_command': 'SET SESSION wsrep_sync_wait = 1;'
    }
else:
    db_options = {}

if 'mysql' in db_backend:
    db_options['charset'] = 'utf8mb4'
JSON_FIELD_AVAILABLE = db_backend in ('mysql', 'postgresql')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.' + db_backend,
        'NAME': config.get(
            'database',
            'name',
            fallback=os.path.join(
                DATA_DIR,
                'db.sqlite3')),
        'USER': config.get(
            'database',
            'user',
            fallback=''),
        'PASSWORD': config.get(
            'database',
            'password',
            fallback=''),
        'HOST': config.get(
            'database',
            'host',
            fallback=''),
        'PORT': config.get(
            'database',
            'port',
            fallback=''),
        'CONN_MAX_AGE': 0 if db_backend == 'sqlite3' else 120,
        'OPTIONS': db_options,
        'TEST': {
            'CHARSET': 'utf8mb4',
            'COLLATION': 'utf8mb4_unicode_ci',
        } if 'mysql' in db_backend else {}
    }
}

STATIC_URL = config.get('urls', 'static', fallback='/static/')

MEDIA_URL = config.get('urls', 'media', fallback='/media/')

SITE_URL = config.get('pretrax', 'url', fallback='http://localhost')
if SITE_URL.endswith('/'):
    SITE_URL = SITE_URL[:-1]

CSRF_TRUSTED_ORIGINS = [urlparse(SITE_URL).hostname]

TRUST_X_FORWARDED_FOR = config.get(
    'pretrax',
    'trust_x_forwarded_for',
    fallback=False)

if config.get('pretrax', 'trust_x_forwarded_proto', fallback=False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = ['*']

LANGUAGE_CODE = config.get('locale', 'default', fallback='en')
TIME_ZONE = config.get('locale', 'timezone', fallback='UTC')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
    }
}

REAL_CACHE_USED = False
SESSION_ENGINE = None

HAS_MEMCACHED = config.has_option('memcached', 'location')
if HAS_MEMCACHED:
    REAL_CACHE_USED = True
    CACHES['default'] = {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': config.get('memcached', 'location'),
    }

HAS_REDIS = config.has_option('redis', 'location')
if HAS_REDIS:
    CACHES['redis'] = {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config.get('redis', 'location'),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
    CACHES['redis_sessions'] = {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config.get('redis', 'location'),
        "TIMEOUT": 3600 * 24 * 30,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
    if not HAS_MEMCACHED:
        CACHES['default'] = CACHES['redis']
        REAL_CACHE_USED = True
    if config.getboolean('redis', 'sessions', fallback=False):
        SESSION_ENGINE = "django.contrib.sessions.backends.cache"
        SESSION_CACHE_ALIAS = "redis_sessions"

if not SESSION_ENGINE:
    if REAL_CACHE_USED:
        SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
    else:
        SESSION_ENGINE = "django.contrib.sessions.backends.db"

HAS_CELERY = config.has_option('celery', 'broker')
if HAS_CELERY:
    CELERY_BROKER_URL = config.get('celery', 'broker')
    CELERY_RESULT_BACKEND = config.get('celery', 'backend')
else:
    CELERY_TASK_ALWAYS_EAGER = True


STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static.dist')

SESSION_COOKIE_NAME = 'pretrax_session'
LANGUAGE_COOKIE_NAME = 'pretrax_language'
CSRF_COOKIE_NAME = 'pretrax_csrftoken'
SESSION_COOKIE_HTTPONLY = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pretrax.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pretrax.wsgi.application'

USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = [
    os.path.join(os.path.dirname(__file__), 'locale'),
]
if config.has_option('languages', 'path'):
    LOCALE_PATHS.insert(0, config.get('languages', 'path'))

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'pretrax/static')
] if os.path.exists(os.path.join(BASE_DIR, 'pretrax/static')) else []

STATICI18N_ROOT = os.path.join(BASE_DIR, "pretrax/static")

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_DEFAULT_QUEUE = 'default'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
