import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-^=85l*&854sfp!k2unp)o0z8u*))$woxg5x0==*6d2sbm*k-s7'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Custom apps
    'accounts.apps.AccountsConfig',
    'movies.apps.MoviesConfig',
    'theaters.apps.TheatersConfig',
    'bookings.apps.BookingsConfig',
    'payments.apps.PaymentsConfig',
    'analytics.apps.AnalyticsConfig',
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

ROOT_URLCONF = 'cineverse.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'movies.context_processors.global_cinema_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'cineverse.wsgi.application'

# Database configuration
# On Vercel serverless functions, the root is read-only.
# We automatically copy the pre-seeded SQLite database to /tmp for full read-write functionality.
DB_FILE = BASE_DIR / 'db.sqlite3'
if os.getenv('VERCEL'):
    import shutil
    TMP_DB = Path('/tmp') / 'db.sqlite3'
    if not TMP_DB.exists() and DB_FILE.exists():
        try:
            shutil.copyfile(DB_FILE, TMP_DB)
        except Exception:
            pass
    DB_NAME = TMP_DB if TMP_DB.exists() else DB_FILE
else:
    DB_NAME = DB_FILE

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DB_NAME,
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        }
    },
]

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'movies:movie_list'
LOGOUT_REDIRECT_URL = 'movies:movie_list'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (Posters, QR codes, PDFs)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Session settings
SESSION_COOKIE_AGE = 86400 * 7
SESSION_SAVE_EVERY_REQUEST = True

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'tickets@cineverse.com'

# Payment Gateway Configuration (Razorpay & Simulation)
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', 'rzp_test_cineverse1234')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', 'secret_cineverse98765')
RAZORPAY_WEBHOOK_SECRET = os.getenv('RAZORPAY_WEBHOOK_SECRET', 'whsec_cineverse_secure')
PAYMENT_SIMULATION_MODE = True  # Allows full testing without live bank keys

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
# Always eager fallback ensures email and ticket tasks execute reliably in local dev environments
CELERY_TASK_ALWAYS_EAGER = True

