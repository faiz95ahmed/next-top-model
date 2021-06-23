from channels.generic.websocket import WebsocketConsumer
import json
from jobs.models import Job, Result

class BenchmarkConsumer(WebsocketConsumer):
    # def connect(self, *args, **kwargs):
    #     super().connect(*args, **kwargs)

    # def disconnect(self):
    #     super().disconnect() 

    def receive(self, text_data=None, *args, **kwargs):
        job_id = json.loads(text_data)
        job = Job.objects.get(id=job_id)
        result = Result.objects.get(job=job, epoch=None).values('id', 'content')
        self.send(json.dumps(result))