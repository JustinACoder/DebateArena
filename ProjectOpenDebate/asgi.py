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
from django.urls import re_path

from discussion.consumers import DiscussionConsumer
from pairing.consumers import PairingConsumer
from notifications.consumers import NotificationConsumer
from .demultiplexer import AsyncJsonWebsocketDemultiplexer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ProjectOpenDebate.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            re_path("^ws/$", AsyncJsonWebsocketDemultiplexer.as_asgi(
                discussion=DiscussionConsumer.as_asgi(),
                notification=NotificationConsumer.as_asgi(),
                pairing=PairingConsumer.as_asgi(),
            ))
        ])
    ),
})
