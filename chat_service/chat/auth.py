
from .rpc import AuthRPCClient


def authenticate_request(request):
    token = request.headers.get("Authorization")
    if not token:
        return None

    if token.startswith("Bearer "):
        token = token.split(" ", 1)[1]

    rpc = AuthRPCClient()
    try:
        data = rpc.verify_token(token)
    finally:
        rpc.close()

    if not data or not data.get("ok"):
        return None

    return data["user"]
