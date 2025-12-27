from rest_framework import serializers
from .models import Task, TaskAttachment, TaskActivityLog

class TaskAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAttachment
        fields = ["id", "file_name", "file_url", "file_size", "mime_type", "uploader_id", "created_at"]
        read_only_fields = ["id", "created_at", "uploader_id"]


class TaskActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskActivityLog
        fields = ["id", "actor_id", "action", "meta", "created_at"]
        read_only_fields = ["id", "created_at"]


class TaskSerializer(serializers.ModelSerializer):
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    activity_logs = TaskActivityLogSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "attachments", "activity_logs"]
