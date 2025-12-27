from django.db import models

class Team(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=12, unique=True) 
    created_by = models.IntegerField() 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    ROLE_MANAGER = "manager"
    ROLE_MEMBER = "member"
    ROLE_CHOICES = (
        (ROLE_MANAGER, "Manager"),
        (ROLE_MEMBER, "Member"),
    )

    team = models.ForeignKey(Team, related_name="members", on_delete=models.CASCADE)
    user_id = models.IntegerField()  
    user_name = models.CharField(max_length=255, blank=True, default="")
    user_email = models.EmailField(blank=True, default="")
    avatar_url = models.CharField(max_length=1000, blank=True, default="")

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("team", "user_id")
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["team"]),
        ]

    def __str__(self):
        return f"{self.user_name or self.user_id} in {self.team.name}"
