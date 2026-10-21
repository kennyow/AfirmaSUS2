"""Inicia o servidor WSGI com configuração de produção."""
import os

from waitress import serve


def main():
    os.environ.setdefault('DJANGO_DEBUG', 'false')
    from setup.wsgi import application
    from django.conf import settings
    from django.core.exceptions import ImproperlyConfigured

    if settings.DEBUG:
        raise ImproperlyConfigured('O servidor de produção exige DJANGO_DEBUG=false.')
    # Um único processo/thread enquanto as gravações em JSON não forem serializadas.
    serve(
        application,
        host=os.environ.get('HOST', '127.0.0.1'),
        port=int(os.environ.get('PORT', '8080')),
        threads=1,
        expose_tracebacks=False,
    )


if __name__ == '__main__':
    main()
