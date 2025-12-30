from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .permissions import IsAuthenticatedByAuthService
from .team_rpc import TeamRPCClient
from .task_rpc import TaskRPCClient
from .openai_client import ask_ai


class ChatBotView(APIView):
    permission_classes = [IsAuthenticatedByAuthService]

    def post(self, request):
        user = request.auth_user
        user_id = user["id"]

        message = request.data.get("message", "").lower()
        if not message:
            return Response(
                {"detail": "message is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        
        if "my task" in message or "assigned to me" in message:
            task_rpc = TaskRPCClient()
            try:
                tasks = task_rpc.get_tasks_for_user(user_id)
            finally:
                task_rpc.close()

            if not tasks:
                return Response({"reply": "You have no assigned tasks."})

            titles = [f"- {t['title']}" for t in tasks[:5]]
            return Response({
                "reply": "Here are your tasks:\n" + "\n".join(titles)
            })

        if "team member" in message or "who is in my team" in message:
            team_rpc = TeamRPCClient()
            try:
                members = team_rpc.get_members_for_user(user_id)
            finally:
                team_rpc.close()

            if not members:
                return Response({"reply": "You are not part of any team."})

            names = [m.get("name", "Unknown") for m in members]
            return Response({
                "reply": "Your team members are: " + ", ".join(names)
            })

        ai_reply = ask_ai(
            user_message=message,
            system_context=(
                f"You are assisting user {user_id} "
                f"inside a task management app."
            )
        )

        return Response({"reply": ai_reply})
