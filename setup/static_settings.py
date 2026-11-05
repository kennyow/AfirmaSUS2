"""Collect static assets without loading SQLite or accessing any database."""
from .pilot_settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}
