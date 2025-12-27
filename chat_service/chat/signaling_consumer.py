import json
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .models import RoomParticipant
from .rpc import AuthRPCClient


class SignalingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.room_id = self.scope["url_route"]["kwargs"].get("room_id")
            if not self.room_id:
                print("WS ERROR: room_id missing")
                await self.close(code=4004)
                return

            query = parse_qs(self.scope["query_string"].decode())
            token = query.get("token", [None])[0]

            if not token:
                print("WS ERROR: token missing")
                await self.close(code=4001)
                return

            user = await self.authenticate(token)
            if not user:
                print("WS ERROR: auth failed")
                await self.close(code=4003)
                return

            self.user_id = user["id"]

            is_member = await self.is_participant()
            if not is_member:
                print(
                    f"WS ERROR: user {self.user_id} not participant of room {self.room_id}"
                )
                await self.close(code=4003)
                return

            self.group_name = f"signal_{self.room_id}"

            await self.accept()

            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name,
            )

            print(
                f"WS CONNECTED: user={self.user_id}, room={self.room_id}"
            )

        except Exception as e:
            print(" WS CONNECT CRASH:", repr(e))
            await self.close(code=1011)

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )
            print(
                f" WS DISCONNECTED: user={getattr(self, 'user_id', None)}, room={getattr(self, 'room_id', None)}"
            )

    async def receive(self, text_data):
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            print("WS WARNING: invalid JSON")
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "signal_message",
                "payload": payload,
                "user_id": self.user_id,
            },
        )

    async def signal_message(self, event):
        await self.send(
            text_data=json.dumps({
                "user_id": event["user_id"],
                "payload": event["payload"],
            })
        )

    @database_sync_to_async
    def is_participant(self):
        return RoomParticipant.objects.filter(
            room_id=self.room_id,
            user_id=self.user_id,
        ).exists()

    @database_sync_to_async
    def authenticate(self, token):
        rpc = AuthRPCClient()
        try:
            data = rpc.verify_token(token)
        finally:
            rpc.close()

        if not data or not data.get("ok"):
            return None

        return data["user"]
