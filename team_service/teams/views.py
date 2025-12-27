import secrets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, EmptyPage
from django.core.mail import send_mail

from .models import Team, TeamMember
from .serializers import TeamSerializer, TeamMemberSerializer
from .permissions import IsAuthenticatedByAuthService


def is_team_manager(user_id, team):
    return TeamMember.objects.filter(
        team=team,
        user_id=user_id,
        role=TeamMember.ROLE_MANAGER
    ).exists()


class CreateTeamView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request):
        user = request.auth_user

        name = request.data.get("name")
        if not name:
            return Response({"detail": "Team name required"}, status=400)

        team = Team.objects.create(
            name=name,
            code=secrets.token_hex(4),
            created_by=user["id"],
        )

        TeamMember.objects.create(
            team=team,
            user_id=user["id"],
            user_name=user.get("full_name", ""),
            user_email=user.get("email", ""),
            role=TeamMember.ROLE_MANAGER,
        )

        return Response(TeamSerializer(team).data, status=201)


class JoinTeamView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request):
        user = request.auth_user

        code = request.data.get("code")
        if not code:
            return Response({"detail": "Invite code required"}, status=400)

        team = get_object_or_404(Team, code=code)

        if TeamMember.objects.filter(team=team, user_id=user["id"]).exists():
            return Response({"detail": "Already a member"}, status=200)

        TeamMember.objects.create(
            team=team,
            user_id=user["id"],
            user_name=user.get("full_name", ""),
            user_email=user.get("email", ""),
            role=TeamMember.ROLE_MEMBER,
        )

        return Response({"detail": "Joined successfully"}, status=201)


class MyTeamsView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def get(self, request):
        user = request.auth_user

        memberships = TeamMember.objects.filter(
            user_id=user["id"]
        ).select_related("team")

        teams = [m.team for m in memberships]

        page = int(request.query_params.get("page", 1))
        per_page = int(request.query_params.get("per_page", 25))

        paginator = Paginator(teams, per_page)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            return Response({"detail": "Page out of range"}, status=400)

        return Response({
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "results": TeamSerializer(page_obj.object_list, many=True).data,
        })


class InviteMemberView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request, team_id):
        user = request.auth_user
        team = get_object_or_404(Team, id=team_id)

        if not is_team_manager(user["id"], team):
            return Response({"detail": "Only managers can invite"}, status=403)

        email = request.data.get("email")
        if not email:
            return Response({"detail": "Email required"}, status=400)

        invite_code = team.code

        subject = f"You are invited to join team: {team.name}"
        message = (
          f"You have been invited to join team '{team.name}'.\n\n"
          f"Use this invite code:\n{invite_code}"
           )

        try:
            send_mail(
                subject,
                message,
                "no-reply@synq.com",
                [email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                {"detail": "Failed to send email", "error": str(e)},
                status=500,
            )

        return Response(
            {"detail": f"Invitation sent to {email}", "code": invite_code},
            status=200,
        )


class TeamMembersView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def get(self, request, team_id):
        user = request.auth_user
        team = get_object_or_404(Team, id=team_id)

        if not TeamMember.objects.filter(team=team, user_id=user["id"]).exists():
            return Response({"detail": "Forbidden"}, status=403)

        members_qs = TeamMember.objects.filter(team=team).order_by("-joined_at")

        page = int(request.query_params.get("page", 1))
        per_page = int(request.query_params.get("per_page", 50))

        paginator = Paginator(members_qs, per_page)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            return Response({"detail": "Page out of range"}, status=400)

        return Response({
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "results": TeamMemberSerializer(page_obj.object_list, many=True).data,
        })


class RemoveMemberView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request, team_id):
        user = request.auth_user
        team = get_object_or_404(Team, id=team_id)

        if not is_team_manager(user["id"], team):
            return Response({"detail": "Only managers can remove members"}, status=403)

        target_user_id = request.data.get("user_id")
        if target_user_id is None:
            return Response({"detail": "user_id required"}, status=400)

        try:
            target_user_id = int(target_user_id)
        except ValueError:
            return Response({"detail": "user_id must be integer"}, status=400)

        if target_user_id == user["id"]:
            return Response({"detail": "Managers cannot remove themselves"}, status=400)

        member = TeamMember.objects.filter(
            team=team,
            user_id=target_user_id
        ).first()

        if not member:
            return Response({"detail": "Member not found"}, status=404)

        member.delete()
        return Response({"detail": "Member removed"}, status=200)


class LeaveTeamView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request, team_id):
        user = request.auth_user
        team = get_object_or_404(Team, id=team_id)

        membership = TeamMember.objects.filter(
            team=team,
            user_id=user["id"]
        ).first()

        if not membership:
            return Response({"detail": "You are not a member"}, status=403)

        if membership.role == TeamMember.ROLE_MANAGER:
            manager_count = TeamMember.objects.filter(
                team=team,
                role=TeamMember.ROLE_MANAGER
            ).count()

            if manager_count == 1:
                return Response(
                    {"detail": "You are the only manager. Transfer management first."},
                    status=400,
                )

        membership.delete()
        return Response({"detail": "Left team successfully"}, status=200)


class MyRoleInTeamView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def get(self, request, team_id):
        user = request.auth_user

        member = TeamMember.objects.filter(
            team_id=team_id,
            user_id=user["id"]
        ).first()

        if not member:
            return Response({"detail": "Not a member"}, status=403)

        return Response({"role": member.role})
