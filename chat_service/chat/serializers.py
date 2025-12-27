from rest_framework import serializers
from .models import Room, Message, MessageAttachment, MessageReceipt, RoomParticipant


class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        fields = ["id", "file"]


class MessageSerializer(serializers.ModelSerializer):
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    reply_to_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "room",
            "sender_id",
            "text",
            "reply_to_id",
            "attachments",
            "created_at",
        ]
        
        read_only_fields = ["room", "sender_id", "created_at"]

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "room_type", "team_id", "created_at"]


class RoomParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomParticipant
        fields = ["room", "user_id"]


class MessageReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageReceipt
        fields = ["message", "user_id", "seen_at"]



