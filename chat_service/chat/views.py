from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import (
    Room,
    RoomParticipant,
    Message,
    MessageAttachment,
    MessageReceipt,
)
from .serializers import RoomSerializer, MessageSerializer
from .team_rpc import TeamRPCClient
from .permissions import IsAuthenticatedByAuthService


def is_participant(room, user_id):
    if room.room_type == "group":
        client = TeamRPCClient()
        try:
            resp = client.check_membership(user_id, room.team_id)
        except Exception:
            return None
        finally:
            client.close()

        if not resp.get("ok"):
            return None

        return resp.get("is_member")

    return RoomParticipant.objects.filter(
        room=room,
        user_id=user_id
    ).exists()


def get_or_create_dm_room(user1_id, user2_id):
    rooms = Room.objects.filter(room_type="dm")
    for room in rooms:
        participants = set(
            room.participants.values_list("user_id", flat=True)
        )
        if participants == {user1_id, user2_id}:
            return room, False

    room = Room.objects.create(room_type="dm")
    RoomParticipant.objects.bulk_create([
        RoomParticipant(room=room, user_id=user1_id),
        RoomParticipant(room=room, user_id=user2_id),
    ])
    return room, True


class CreateTeamRoomView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request):
        user = request.auth_user
        team_id = request.data.get("team_id")

        if not team_id:
            return Response({"detail": "team_id required"}, status=400)

        client = TeamRPCClient()
        try:
            resp = client.check_membership(user["id"], team_id)
        except Exception:
            return Response(
                {"detail": "Team service unavailable"},
                status=503,
            )
        finally:
            client.close()

        if not resp.get("is_member"):
            return Response(status=403)

        room, _ = Room.objects.get_or_create(
            room_type="group",
            team_id=team_id,
        )

        return Response(RoomSerializer(room).data, status=201)


class CreateDMRoomView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request):
        user = request.auth_user
        other_user_id = request.data.get("user_id")

        if not other_user_id:
            return Response({"detail": "user_id required"}, status=400)

        if other_user_id == user["id"]:
            return Response(
                {"detail": "Cannot create DM with yourself"},
                status=400,
            )

        room, _ = get_or_create_dm_room(
            user["id"],
            other_user_id
        )

        return Response(RoomSerializer(room).data, status=201)


class MessageListCreateView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def get(self, request, room_id):
        user = request.auth_user
        room = get_object_or_404(Room, id=room_id)

        allowed = is_participant(room, user["id"])
        if allowed is None:
            return Response(
                {"detail": "Team service unavailable"},
                status=503,
            )
        if not allowed:
            return Response(status=403)

        messages = (
            Message.objects
            .filter(room=room)
            .order_by("created_at")
        )

        return Response(
            MessageSerializer(messages, many=True).data
        )

    def post(self, request, room_id):
        user = request.auth_user
        room = get_object_or_404(Room, id=room_id)

        allowed = is_participant(room, user["id"])
        if allowed is None:
            return Response(
                {"detail": "Team service unavailable"},
                status=503,
            )
        if not allowed:
            return Response(status=403)

        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.save(
            room=room,
            sender_id=user["id"],
        )

        for f in request.FILES.getlist("files"):
            MessageAttachment.objects.create(
                message=message,
                file=f,
            )

        return Response(
            MessageSerializer(message).data,
            status=201,
        )


class MarkSeenView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request, message_id):
        user = request.auth_user
        message = get_object_or_404(Message, id=message_id)

        allowed = is_participant(message.room, user["id"])
        if allowed is None:
            return Response(
                {"detail": "Team service unavailable"},
                status=503,
            )
        if not allowed:
            return Response(status=403)

        MessageReceipt.objects.get_or_create(
            message=message,
            user_id=user["id"],
        )

        return Response({"status": "seen"}, status=200)
