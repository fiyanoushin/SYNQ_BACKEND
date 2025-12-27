import requests
from django.conf import settings
from .rpc import auth_rpc

def authenticate(request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None

    token = auth.split(" ")[1]
    result = auth_rpc.validate(token)
    if not result.get("ok"):
        return None

    return result["user"], token


def is_member(token, team_id, user_id):
    url = f"{settings.TEAM_SERVICE_URL}/teams/{team_id}/members/"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code != 200:
            return False

        for m in res.json():
            if m["user_id"] == user_id:
                return True
        return False
    except:
        return False
