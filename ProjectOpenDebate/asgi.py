"""
ASGI config for ProjectOpenDebate project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from .consumers import UserConsumer
from django.urls import path

from discussion.handlers import config as discussion_handler_config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ProjectOpenDebate.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/", UserConsumer.as_asgi(
                discussion=discussion_handler_config
            )),
        ])
    ),
})
