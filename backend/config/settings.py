import os
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY=os.getenv('DJANGO_SECRET_KEY','dev-only-change-me')
DEBUG=os.getenv('DEBUG','false').lower()=='true'
ALLOWED_HOSTS=[x.strip() for x in os.getenv('ALLOWED_HOSTS','localhost,127.0.0.1,.onrender.com').split(',') if x.strip()]
INSTALLED_APPS=['django.contrib.contenttypes','django.contrib.staticfiles','rest_framework','corsheaders','routing']
MIDDLEWARE=['corsheaders.middleware.CorsMiddleware','django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.middleware.common.CommonMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[]
WSGI_APPLICATION='config.wsgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
STATIC_URL='static/'
STATIC_ROOT=BASE_DIR/'staticfiles'
CORS_ALLOWED_ORIGINS=[x.strip() for x in os.getenv('CORS_ALLOWED_ORIGINS','http://localhost:5173').split(',') if x.strip()]
# Permit this project's immutable Vercel deployment URLs as well as the production alias.
CORS_ALLOWED_ORIGIN_REGEXES=[r'^https://spotter-weather-routing(?:-[a-z0-9]+)?-faizanali2k05\.vercel\.app$']
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
]
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
