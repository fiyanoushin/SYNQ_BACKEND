from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status
from .auth_rpc_client import AuthRPCClient


class IsAuthenticatedByAuthService(BasePermission):
    

    def has_permission(self, request, view):
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return False

        token = auth.split(" ", 1)[1]

        auth_rpc = AuthRPCClient()
        res = auth_rpc.validate_token(token)

        if not res.get("ok"):
            return False

        request.auth_user = res["user"]
        return True
