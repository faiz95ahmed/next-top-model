from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from jobs.models import Job, Result, Log
from jobs.util import JobStatus
from collections import defaultdict
from next_top_model.settings import _redis
import traceback

class GraphConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        try:
            self.abort_received = set()
            # print("INITIATING GRAPH CONSUMER")
            super().__init__(*args, **kwargs)
            # print("GRAPH CONSUMER INITIATED")
        except Exception as e:
            print('__init__ ', e)
            raise e

    async def connect(self):
        try:
            # print("CONNECTING")
            await self.channel_layer.group_add('realtime_data', self.channel_name)
            await super().connect()
            # print("CONNECTED")
            await self.send_initial_data()
        except Exception as e:
            print('connect ', e)
            raise e

    async def disconnect(self):
        try:
            # print("DISCONNECTING FOR SOME REASON")
            await self.channel_layer.group_discard('realtime_data', self.channel_name)
            # await super().disconnect() 
        except Exception as e:
            print('disconnect ', e)
            raise e

    async def send_job_data(self, event: dict):
        try:
            # print("DATA RECEIVED")
            event["type"] = "job_data"
            # print(event)
            await self.send(json.dumps(event))
            # print("NEW DATA SENT")
        except Exception as e:
            print('send_job_data ', e)
            raise e
    
    async def receive(self, text_data=None, bytes_data=None):
        try:
            # print("SOMETHING ELSE RECIEVED")
            e = json.loads(text_data)
            if e["type"] == "abort":
                job_id = e["args"]["job_id"]
                if job_id not in self.abort_received:
                    job_abort_key = "job_{}_abort".format(job_id)
                    _redis.lpush(job_abort_key, "MANUAL")
                else:
                    self.abort_received.add(job_id)
                print("abort signal recieved for {}".format(job_id))
                await self.ack_abort_recieved(job_id)
            else:
                print("Unrecognised command to consumer") 
        except Exception as e:
            print('receive ', e)
            raise e
    
    async def ack_abort_recieved(self, job_id):
        try:
            await self.send(json.dumps({
                    "type": "consumer_response",
                    "response": {
                        "type": "consumer_received_abort",
                        "data": {
                            "job_id": job_id
                        }
                    }
                }))
        except Exception as e:
            print('ack_abort_recieved ', e)
            raise e
 
    async def websocket_connect(self, message):
        try:
            return await super().websocket_connect(message)
        except Exception as e:
            print('websocket_connect ', e)
            raise e
    
    async def websocket_receive(self, message):
        try:
            return await super().websocket_receive(message)
        except Exception as e:
            print('websocket_receive ', e)
            raise e
    
    async def websocket_disconnect(self, message):
        try:
            return await super().websocket_disconnect(message)
        except Exception as e:
            print('websocket_disconnect ', e)
            raise e
    
    async def __call__(self, *args, **kwargs):
        try:
            return await super().__call__(*args, **kwargs)
        except Exception as e:
            print('__call__ ', e)
            traceback.print_exc()
            raise e

    async def dispatch(self, message):
        try:
            return await super().dispatch(message)
        except Exception as e:
            print('dispatch ', e)
            raise e

    async def send(self, message):
        try:
            return await super().send(message)
        except Exception as e:
            print('send ', e)
            raise e

    async def close(self, *args, **kwargs):
        try:
            return await super().close(*args, **kwargs)
        except Exception as e:
            print('close ', e)
            raise e

    async def send_initial_data(self):
        try:
            # get active jobs from DB
            active_jobs = await database_sync_to_async(self.get_active_jobs)()
            # print(active_jobs)
            # print(list(active_jobs))
            # print("SENDING INITIAL DATA!")
            all_data = {}
            for job, is_bench in active_jobs:
                progress = defaultdict(dict) # map of epoch num -> (map of series name -> (progress and loss))
                logs = []
                # get intial data from DB
                model_name = await database_sync_to_async(self.get_model_title)(job)
                logs_raw = await database_sync_to_async(self.get_logs)(job)
                epoch = 0
                for progress_obj in (await database_sync_to_async(self.get_results)(job)):
                    progress[progress_obj.epoch] = progress_obj.content
                    if progress_obj.epoch is not None:
                        epoch = max(epoch, progress_obj.epoch)#
                # construct log dicts
                for log in logs_raw:
                    log["time"] = str(log["time"])
                    log["relativeCreated"] = "{:10.3f}".format(log["relativeCreated"])
                    logs.append(log)
                all_data[job.id] = {"logs": logs,
                                "progress": progress,
                                "abort_ack": False,
                                "model_name": model_name,
                                "is_bench": is_bench}
            message = {'type': 'job_data', 'all_data': json.dumps(all_data)}
            await self.send(json.dumps(message))
            # print("INITIAL DATA SENT")
        except Exception as e:
            print('send_initial_data ', e)
            raise e

    def get_active_jobs(self):
        try:
            # print("GETTING ACTIVE JOBS")
            return [(j, j.benchmark is not None) for j in list(Job.objects.filter(status=JobStatus.RUNNING))]
        except Exception as e:
            print('get_active_jobs ', e)
            raise e

    def get_logs(self, job):
        try:
            return list(Log.objects.filter(job=job).order_by('relativeCreated').values('message', 'relativeCreated', 'log_level', 'time'))
        except Exception as e:
            print('get_logs ', e)
            raise e

    def get_results(self, job):
        try:
            return list(Result.objects.filter(job=job))
        except Exception as e:
            print('get_results ', e)
            raise e

    def get_model_title(self, job):
        try:
            return job.mlmodel.title
        except Exception as e:
            print('get_model_title ', e)
            raise e