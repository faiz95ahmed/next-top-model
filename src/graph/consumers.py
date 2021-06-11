from channels.generic.websocket import AsyncWebsocketConsumer
import json
from time import sleep

class GraphConsumer(AsyncWebsocketConsumer):
    async def connect(self, *args, **kwargs):
        await self.channel_layer.group_add('training_data', self.channel_name)
        await self.accept()

    async def disconnect(self):
        await self.channel_layer.group_discard('training_data', self.channel_name)
        await super().disconnect() 

    async def send_job_data(self, event: dict):
        event.pop("type")
        await self.send(json.dumps(event))
        
        