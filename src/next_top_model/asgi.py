"""
ASGI config for next_top_model project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

from graph.routing import ws_urlpatterns as graph_patterns
from activities.routing import ws_urlpatterns as bench_patterns

from django.urls import path
from activities.consumers import BenchmarkConsumer
from graph.consumers import GraphConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'next_top_model.settings')
ws_urlpatterns = [
    path('ws/benchmark/', BenchmarkConsumer.as_asgi()),
    path('ws/graph/', GraphConsumer.as_asgi()),
]
application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(URLRouter(ws_urlpatterns))
})
