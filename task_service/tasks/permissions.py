from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed
from .rpc import AuthRPCClient


class IsAuthenticatedByAuthService(BasePermission):
    

    def has_permission(self, request, view):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            raise AuthenticationFailed("Authorization header missing")

        if not auth_header.startswith("Bearer "):
            raise AuthenticationFailed("Invalid authorization header format")

        token = auth_header.split(" ", 1)[1].strip()

        if not token:
            raise AuthenticationFailed("Token missing")

        auth_rpc = AuthRPCClient()

        try:
            res = auth_rpc.validate_token(token)
        except Exception:
            
            raise AuthenticationFailed("Auth service unavailable")

        if not res or not res.get("ok"):
            raise AuthenticationFailed("Invalid or expired token")

        user = res.get("user")

        if not user or "id" not in user:
            raise AuthenticationFailed("Invalid auth response")

       
        request.auth_user = user
        return True
