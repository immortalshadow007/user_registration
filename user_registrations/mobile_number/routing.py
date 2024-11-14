# mobile_number/routing.py
from django.urls import path
from . import consumers

# Define WebSocket URL patterns
websocket_urlpatterns = [
    path('ws/mobile_number/', consumers.MobileNumberConsumer.as_asgi()),
]
