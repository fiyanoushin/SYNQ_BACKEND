from django.urls import re_path
from .consumers import ChatConsumer
from .signaling_consumer import SignalingConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_id>\d+)/$", ChatConsumer.as_asgi()),
    re_path(r"ws/video/(?P<room_id>\d+)/$", SignalingConsumer.as_asgi()),
]
