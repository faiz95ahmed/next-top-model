from django.urls import path
from .consumers import BenchmarkConsumer

ws_urlpatterns = [
    path('ws/benchmark/', BenchmarkConsumer.as_asgi())
]