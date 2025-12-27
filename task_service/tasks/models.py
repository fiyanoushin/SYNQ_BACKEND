from django.db import models

class Task(models.Model):
    STATUS_CHOICES = (
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("done", "Done"),
    )

    PRIORITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    team_id = models.IntegerField()
    created_by = models.IntegerField()
    assigned_to = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="todo")
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default="medium")
    due_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class TaskAttachment(models.Model):
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    uploader_id = models.IntegerField()
    file_name = models.TextField()
    file_url = models.TextField()
    file_size = models.BigIntegerField(null=True, blank=True)
    mime_type = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_name} ({self.task_id})"


class TaskActivityLog(models.Model):
   
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="activity_logs")
    actor_id = models.IntegerField()
    action = models.CharField(max_length=64)
    meta = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} by {self.actor_id} on {self.created_at}"
