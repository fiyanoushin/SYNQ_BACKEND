import uuid
import boto3

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Task, TaskAttachment, TaskActivityLog
from .serializers import (
    TaskSerializer,
    TaskAttachmentSerializer,
    TaskActivityLogSerializer,
)
from .permissions import IsAuthenticatedByAuthService
from .team_client import TeamRPCClient


# ---------- helpers ----------

def create_activity(task, actor_id, action, meta=None):
    TaskActivityLog.objects.create(
        task=task,
        actor_id=actor_id,
        action=action,
        meta=meta or {},
    )


def get_team_role(user_id, team_id):
    client = TeamRPCClient()
    return client.get_role(user_id, team_id)


def ensure_task_access(user, task):
   
    role = get_team_role(user["id"], task.team_id)
    if not role:
        return False

    if role == "manager":
        return True

    return task.assigned_to and task.assigned_to == user["id"]




class CreateTaskView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request):
        user = request.auth_user
        team_id = request.data.get("team_id")
        assigned_to = request.data.get("assigned_to")

        if not team_id:
            return Response({"detail": "team_id required"}, status=400)

        if not assigned_to:
            return Response({"detail": "assigned_to required"}, status=400)

        role = get_team_role(user["id"], team_id)
        if role != "manager":
            return Response({"detail": "Only managers can create tasks"}, status=403)

        if not get_team_role(assigned_to, team_id):
            return Response({"detail": "Assignee not in team"}, status=400)

        serializer = TaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = serializer.save(
            team_id=team_id,
            created_by=user["id"],
            assigned_to=assigned_to,
        )

        create_activity(task, user["id"], "task_created")
        return Response(TaskSerializer(task).data, status=201)


class ListTasksView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def get(self, request):
        user = request.auth_user
        team_id = request.query_params.get("team_id")

        if not team_id:
            return Response({"detail": "team_id required"}, status=400)

        role = get_team_role(user["id"], team_id)
        if not role:
            return Response({"detail": "Forbidden"}, status=403)

        if role == "manager":
            tasks = Task.objects.filter(team_id=team_id)
        else:
            tasks = Task.objects.filter(
                team_id=team_id,
                assigned_to=user["id"],
            )

        return Response(TaskSerializer(tasks, many=True).data)


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def get(self, request, pk):
        user = request.auth_user
        task = get_object_or_404(Task, pk=pk)

        if not ensure_task_access(user, task):
            return Response({"detail": "Not your task"}, status=403)

        return Response(TaskSerializer(task).data)

    def put(self, request, pk):
        user = request.auth_user
        task = get_object_or_404(Task, pk=pk)

        role = get_team_role(user["id"], task.team_id)
        if role != "manager":
            return Response({"detail": "Only managers can update tasks"}, status=403)

        serializer = TaskSerializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = serializer.save()

        create_activity(task, user["id"], "task_updated")
        return Response(TaskSerializer(task).data)

    def delete(self, request, pk):
        user = request.auth_user
        task = get_object_or_404(Task, pk=pk)

        role = get_team_role(user["id"], task.team_id)
        if role != "manager":
            return Response({"detail": "Only managers can delete"}, status=403)

        task.delete()
        return Response({"detail": "Deleted"})


class AssignTaskView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request, pk):
        user = request.auth_user
        task = get_object_or_404(Task, pk=pk)

        role = get_team_role(user["id"], task.team_id)
        if role != "manager":
            return Response({"detail": "Only managers can assign"}, status=403)

        assignee = request.data.get("user_id")
        if not assignee:
            return Response({"detail": "user_id required"}, status=400)

        if not get_team_role(assignee, task.team_id):
            return Response({"detail": "Assignee not in team"}, status=400)

        task.assigned_to = assignee
        task.save()

        create_activity(task, user["id"], "assignee_changed")
        return Response(TaskSerializer(task).data)


class ChangeStatusView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request, pk):
        user = request.auth_user
        task = get_object_or_404(Task, pk=pk)

        if not ensure_task_access(user, task):
            return Response({"detail": "Not your task"}, status=403)

        status_val = request.data.get("status")
        if status_val not in dict(Task.STATUS_CHOICES):
            return Response({"detail": "Invalid status"}, status=400)

        task.status = status_val
        task.save()

        create_activity(task, user["id"], "status_changed")
        return Response(TaskSerializer(task).data)


class PresignAttachmentView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request, pk):
        user = request.auth_user
        task = get_object_or_404(Task, pk=pk)

        if not ensure_task_access(user, task):
            return Response({"detail": "Not your task"}, status=403)

        filename = request.data.get("filename")
        if not filename:
            return Response({"detail": "filename required"}, status=400)

        key = f"tasks/{task.id}/{uuid.uuid4().hex}_{filename}"

        s3 = boto3.client("s3")
        url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.AWS_S3_BUCKET, "Key": key},
            ExpiresIn=3600,
        )

        return Response({"upload_url": url, "file_key": key})


class ConfirmAttachmentView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request, pk):
        user = request.auth_user
        task = get_object_or_404(Task, pk=pk)

        if not ensure_task_access(user, task):
            return Response({"detail": "Not your task"}, status=403)

        attachment = TaskAttachment.objects.create(
            task=task,
            uploader_id=user["id"],
            file_name=request.data.get("file_name"),
            file_url=request.data.get("file_url"),
        )

        return Response(TaskAttachmentSerializer(attachment).data, status=201)


class TaskLogsView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def get(self, request, pk):
        user = request.auth_user
        task = get_object_or_404(Task, pk=pk)

        if not ensure_task_access(user, task):
            return Response({"detail": "Not your task"}, status=403)

        logs = task.activity_logs.order_by("-id")
        return Response(TaskActivityLogSerializer(logs, many=True).data)
