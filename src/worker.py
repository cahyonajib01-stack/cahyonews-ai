from workers import asgi

from main import app

Default = asgi.entrypoint(app)
