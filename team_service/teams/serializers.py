from rest_framework import serializers
from .models import Team, TeamMember

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "code", "created_by", "created_at"]
        read_only_fields = ["id", "code", "created_by", "created_at"]


class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = [
            "id",
            "team",
            "user_id",
            "user_name",
            "user_email",
            "avatar_url",
            "role",
            "joined_at",
        ]
        read_only_fields = ["id", "joined_at", "team", "user_id"]