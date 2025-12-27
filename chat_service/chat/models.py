from django.db import models
from django.utils import timezone


class Room(models.Model):
    ROOM_TYPE_CHOICES = (
        ("group", "Group"),
        ("dm", "Direct"),
    )

    id = models.BigAutoField(primary_key=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPE_CHOICES)
    team_id = models.IntegerField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["room_type", "team_id"]),
        ]


class RoomParticipant(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="participants")
    user_id = models.IntegerField()
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("room", "user_id")


class Message(models.Model):
    id = models.BigAutoField(primary_key=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    sender_id = models.IntegerField()
    text = models.TextField(blank=True)
    reply_to = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replies"
    )
    created_at = models.DateTimeField(auto_now_add=True)


class MessageAttachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="chat_attachments/", null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class MessageReceipt(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="receipts")
    user_id = models.IntegerField()
    seen_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("message", "user_id")


