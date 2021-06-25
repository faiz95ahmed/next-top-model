from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from jobs.models import Result
class BenchmarkConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def connect(self, *args, **kwargs):
        await self.accept()

    async def receive(self, text_data=None, *args, **kwargs):
        print("MESSAGE RECIEVED " + text_data)
        job_id = json.loads(text_data)
        print("DECODED")
        result = await database_sync_to_async(self.get_job_results)(job_id)
        print("RESULT FOUND "+ json.dumps(result))
        await self.send(json.dumps(result))
    
    def get_job_results(self, job_id):
        print("SEARCHING FOR RESULT", job_id, type(job_id))
        try:
            r = Result.objects.get(job__pk=job_id, epoch=None)
        except Exception as e:
            print(e)
            raise e
        print("RECORD FOUND")
        return {'id': r.job.id, 'content': r.content}