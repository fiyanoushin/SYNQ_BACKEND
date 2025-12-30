from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed
from .rpc import AuthRPCClient


class IsAuthenticatedByAuthService(BasePermission):

    def has_permission(self, request, view):
        # Avoid duplicate auth calls
        if hasattr(request, "auth_user"):
            return True

        auth = request.headers.get("Authorization")

        if not auth or not auth.startswith("Bearer "):
            raise AuthenticationFailed("Authorization header missing or invalid")

        token = auth.split(" ", 1)[1].strip()
        if not token:
            raise AuthenticationFailed("Token missing")

        rpc = AuthRPCClient()
        try:
            res = rpc.verify_token(token)
        except TimeoutError:
            raise AuthenticationFailed("Auth service timeout")
        except Exception:
            raise AuthenticationFailed("Auth service unavailable")
        finally:
            rpc.close()

        if not res or not res.get("ok"):
            raise AuthenticationFailed("Invalid or expired token")

        user = res.get("user")
        if not user or "id" not in user:
            raise AuthenticationFailed("Invalid auth response")

        # ✅ DO NOT touch Django auth system
        request.auth_user = user
        request.auth = user  # optional, but DRF-friendly

        return True
