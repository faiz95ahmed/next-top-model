from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from jobs.models import Job, Result, Log
from jobs.util import JobStatus
from collections import defaultdict

class GraphConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        print("INITIATING GRAPH CONSUMER")
        super().__init__(*args, **kwargs)
        print("GRAPH CONSUMER INITIATED")

    async def connect(self, *args, **kwargs):
        print("CONNECTING")
        await self.channel_layer.group_add('realtime_data', self.channel_name)
        await self.accept()
        print("CONNECTED")
        await self.send_initial_data()

    async def disconnect(self):
        await self.channel_layer.group_discard('realtime_data', self.channel_name)
        # await super().disconnect() 

    async def send_job_data(self, event: dict):
        event.pop("type")
        # print(event)
        await self.send(json.dumps(event))
        print("NEW DATA SENT")
        
    async def send_initial_data(self):
        # get active jobs from DB
        active_jobs = await database_sync_to_async(self.get_active_jobs)()
        print(active_jobs)
        # print(list(active_jobs))
        print("SENDING INITIAL DATA!")
        all_data = {}
        for job in active_jobs:
            progress = defaultdict(dict) # map of epoch num -> (map of series name -> (progress and loss))
            logs = []
            # get intial data from DB
            model_name = await database_sync_to_async(self.get_model_title)(job)
            logs_raw = await database_sync_to_async(self.get_logs)(job)
            epoch = 0
            for progress_obj in (await database_sync_to_async(self.get_results)(job)):
                progress[progress_obj.epoch] = progress_obj.content
                epoch = max(epoch, progress_obj.epoch)#
            # construct log dicts
            for log in logs_raw:
                log["time"] = str(log["time"])
                log["relativeCreated"] = "{:10.3f}".format(log["relativeCreated"])
                logs.append(log)
            all_data[job.id] = {"logs": logs,
                            "progress": progress,
                            "abort_ack": False,
                            "model_name": model_name}
        message = {'all_data': all_data}
        await self.send(json.dumps(message))
        print("INITIAL DATA SENT")

    def get_active_jobs(self):
        print("GETTING ACTIVE JOBS")
        return list(Job.objects.filter(status=JobStatus.RUNNING))

    def get_logs(self, job):
        return list(Log.objects.filter(job=job).order_by('relativeCreated').values('message', 'relativeCreated', 'log_level', 'time'))

    def get_results(self, job):
        return list(Result.objects.filter(job=job))

    def get_model_title(self, job):
        return job.mlmodel.title