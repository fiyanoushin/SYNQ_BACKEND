import json
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .models import RoomParticipant
from .rpc import AuthRPCClient


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]

        query = parse_qs(self.scope["query_string"].decode())
        token = query.get("token", [None])[0]

        if not token:
            await self.close(code=4001)  
            return

        user = await self.authenticate(token)
        if not user:
            await self.close(code=4003)  

        self.user_id = user["id"]

        if not await self.is_participant():
            await self.close(code=4003)
            return

        self.group_name = f"chat_{self.room_id}"
        await self.channel_layer.group_add(
            self.group_name, self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get("type") == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "typing_event",
                    "user_id": self.user_id,
                },
            )

    async def typing_event(self, event):
        await self.send(text_data=json.dumps(event))

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
