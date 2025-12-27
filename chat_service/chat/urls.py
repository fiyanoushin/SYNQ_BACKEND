from django.urls import path
from .views import (
    CreateTeamRoomView,
    CreateDMRoomView,
    MessageListCreateView,
    MarkSeenView,
)
from .bot_views import ChatBotView

urlpatterns = [
    path("rooms/team/", CreateTeamRoomView.as_view()),
    path("rooms/dm/", CreateDMRoomView.as_view()),
    path("rooms/<int:room_id>/messages/", MessageListCreateView.as_view()),
    path("messages/<int:message_id>/seen/", MarkSeenView.as_view()),
    path("bot/", ChatBotView.as_view()),
]
