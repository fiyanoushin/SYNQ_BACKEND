from django.urls import path
from .views import (
    CreateTeamView, JoinTeamView, MyTeamsView, TeamMembersView, RemoveMemberView,LeaveTeamView,InviteMemberView,MyRoleInTeamView,
)

urlpatterns = [
    path("teams/create/", CreateTeamView.as_view(), name="create-team"),
    path("teams/join/", JoinTeamView.as_view(), name="join-team"),
    path("teams/my/", MyTeamsView.as_view(), name="my-teams"),
    path("teams/<int:team_id>/members/", TeamMembersView.as_view(), name="team-members"),
    path("teams/<int:team_id>/members/remove/", RemoveMemberView.as_view(), name="remove-member"),
    path("<int:team_id>/leave/", LeaveTeamView.as_view(), name="leave-team"),
    path("teams/<int:team_id>/invite/", InviteMemberView.as_view(), name="invite-member"),
    path("teams/<int:team_id>/me/role/",MyRoleInTeamView.as_view()),

]
