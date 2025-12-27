from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Room, RoomParticipant, Message, MessageAttachment, MessageReceipt
from .serializers import RoomSerializer, MessageSerializer
from .auth import authenticate_request
from .team_rpc import TeamRPCClient


def is_participant(room, user_id):
    return RoomParticipant.objects.filter(room=room, user_id=user_id).exists()

class CreateTeamRoomView(APIView):
    permission_classes = []

    def post(self, request):
        user = authenticate_request(request)
        if not user:
            return Response(status=403)

        team_id = request.data.get("team_id")
        if not team_id:
            return Response({"detail": "team_id required"}, status=400)

        team_rpc = TeamRPCClient()
        try:
            team_resp = team_rpc.check_membership(user["id"], team_id)
        finally:
            team_rpc.close()

        if not team_resp.get("ok") or not team_resp.get("is_member"):
            return Response(status=403)

        room, _ = Room.objects.get_or_create(
            room_type="group",
            team_id=team_id,
        )

        RoomParticipant.objects.get_or_create(
            room=room,
            user_id=user["id"],
        )

        return Response(RoomSerializer(room).data)




class CreateDMRoomView(APIView):
    permission_classes = []

    def post(self, request):
        user = authenticate_request(request)
        if not user:
            return Response(status=403)

        other_user_id = request.data.get("user_id")

        room = Room.objects.create(room_type="dm")
        RoomParticipant.objects.bulk_create([
            RoomParticipant(room=room, user_id=user["id"]),
            RoomParticipant(room=room, user_id=other_user_id),
        ])

        return Response(RoomSerializer(room).data)


class MessageListCreateView(APIView):
    permission_classes = []

    def get(self, request, room_id):
        user = authenticate_request(request)
        if not user:
            return Response(status=403)

        room = get_object_or_404(Room, id=room_id)
        if not is_participant(room, user["id"]):
            return Response(status=403)

        msgs = Message.objects.filter(room=room).order_by("created_at")
        return Response(MessageSerializer(msgs, many=True).data)

    def post(self, request, room_id):
        user = authenticate_request(request)
        if not user:
            return Response(status=403)

        room = get_object_or_404(Room, id=room_id)
        if not is_participant(room, user["id"]):
            return Response(status=403)

        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        msg = serializer.save(
            room=room,
            sender_id=user["id"],
        )

        for f in request.FILES.getlist("files"):
            MessageAttachment.objects.create(message=msg, file=f)

        return Response(MessageSerializer(msg).data, status=201)


class MarkSeenView(APIView):
    permission_classes = []

    def post(self, request, message_id):
        user = authenticate_request(request)
        if not user:
            return Response(status=403)

        msg = get_object_or_404(Message, id=message_id)
        if not is_participant(msg.room, user["id"]):
            return Response(status=403)

        MessageReceipt.objects.get_or_create(
            message=msg,
            user_id=user["id"],
        )

        return Response({"status": "seen"})
