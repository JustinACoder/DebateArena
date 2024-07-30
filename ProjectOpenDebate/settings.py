"""
Django settings for ProjectOpenDebate project.

Generated by 'django-admin startproject' using Django 5.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
from django.contrib import messages
import os
import environ
from django.urls import reverse

env = environ.Env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
env_file = os.path.join(BASE_DIR, ".env")
environ.Env.read_env(env_file)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# TODO: The .env file doesn't get pushed to github, so the SECRET_KEY is not available in the repository
#  Therefore, we set a default value for the SECRET_KEY here
#  However, this is not a good long term solution as we could forget to set .env in production
#  It would also require us to set a default value for every environment variable in the code which is not ideal
#  Therefore, we must search for better solutions to this problem in the future
SECRET_KEY = env("SECRET_KEY", default="django-insecure$@&!")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'daphne',
    'channels',
    'django_extensions',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    #'allauth.socialaccount.providers.google',
    'debug_toolbar',
    'voting',
    'crispy_forms',
    'crispy_bootstrap5',
    'debate.apps.DebateConfig',
    'users.apps.UsersConfig',
    "discussion.apps.DiscussionConfig",
    "debateme.apps.DebatemeConfig"
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"

ASGI_APPLICATION = 'ProjectOpenDebate.asgi.application'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'ProjectOpenDebate.urls'

INTERNAL_IPS = [
    "127.0.0.1",
]

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
            ],
        },
    },
]

WSGI_APPLICATION = 'ProjectOpenDebate.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Channel layer definitions
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
    # Change to redis layer for production
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
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

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

# In addition to the default static files directory (one in each app), we also have a global static files directory
# This directory is used for global static files, such as CSS files that are used across multiple apps
STATICFILES_DIRS = [
    BASE_DIR / 'static'
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Allauth settings
ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/login/'
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[DebateArena] '
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_CHANGE_EMAIL = True
ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False
ACCOUNT_USERNAME_VALIDATORS = 'users.validators.username_validators'
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 7  # One week
ACCOUNT_FORMS = {
    'signup': 'users.forms.CustomSignupForm',
    'reset_password_from_key': 'users.forms.CustomResetPasswordKeyForm',
    'change_password': 'users.forms.CustomChangePasswordForm',
}

# Email backend settings
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"  # TODO: Change to real email backend in production
EMAIL_SUBJECT_PREFIX = '[DebateArena] '
DEFAULT_FROM_EMAIL = 'noreply@debatearena.com'

# Pagination settings
ENDLESS_PAGINATION_SETTINGS = {
    'FIRST_PAGE_SIZE': 50,  # The size of the first page of a paginated list
    'PAGE_SIZE': 30,  # The size of the rest of the pages
}


# Admins
ADMINS = [
    ('Admin', env("ADMIN_EMAIL", default="admin@gmail.com"))
]
