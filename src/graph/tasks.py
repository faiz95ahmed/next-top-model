from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from celery import shared_task
import logging
import json
import redis
from next_top_model.settings import REDIS_PORT
import GPUtil
from jobs.models import Job
from pathlib import Path

channel_layer = get_channel_layer()
_redis = redis.Redis(host = 'localhost', port = REDIS_PORT, db = 0)
time_formatter = logging.Formatter('%(asctime)s')
order_formatter = logging.Formatter('%(relativeCreated)10d')
message_formatter = logging.Formatter('%(message)s')
logging.basicConfig(
      level=logging.DEBUG,
      handlers=[logging.StreamHandler(), logging.FileHandler('/home/faiz/Desktop/next-top-model/log2.log')]
)
logger = logging.getLogger('JOBNAME')

@shared_task(name='next_top_model.graph.tasks.get_logs')
def get_logs(gpu_id: int):
    n_jobs_on_gpu = Job.objects.filter(active=True, gpu=gpu_id).count()
    if n_jobs_on_gpu > 0:
        curr_job = Job.objects.filter(active=True, gpu=gpu_id)[0]
        job_id = curr_job.id
        job_name = "job_{}".format(str(job_id))
        gpus = [g for g in GPUtil.getGPUs() if g.id == gpu_id]
        gpu_load = gpus[0].load if len(gpus) > 0 else 0
        running = True
        i, j = 0, 0
        logs = []
        progress = {} # map of epoch to progress values
        epoch = None
        abort_ack = False
        while running:
            j += 1
            x = _redis.lpop(job_name)
            if x is not None:
                i += 1
                d = json.loads(x)
                record = logging.makeLogRecord(d)
                if record.name == "STDERR" or record.name == "STDOUT":
                    formatted_message = message_formatter.format(record)
                    formatted_order = order_formatter.format(record)
                    formatted_time = time_formatter.formatTime(record)
                    loglevel = record.levelname
                    logdict = {
                        "message": formatted_message,
                        "order": formatted_order,
                        "time": formatted_time,
                        "level": loglevel
                    }
                    logs.append(logdict)
                    
                elif record.name == "PROGRESS":
                    progress_dict = json.loads(record.msg)
                    epoch_num = progress_dict["epoch"]
                    if epoch is None:
                        epoch = epoch_num
                    else:
                        epoch = max(epoch, epoch_num)
                    if epoch_num in progress.keys():
                        logger.log(logging.DEBUG, progress_dict)
                        if progress_dict["train_progress"] > progress[epoch_num]["train_progress"]:
                            progress[epoch_num]["train_progress"] = progress_dict["train_progress"]
                            progress[epoch_num]["train_loss"] = progress_dict["train_loss"]
                        if progress_dict["validation_progress"] > progress[epoch_num]["validation_progress"]:
                            progress[epoch_num]["validation_progress"] = progress_dict["validation_progress"]
                            progress[epoch_num]["validation_loss"] = progress_dict["validation_loss"]
                    else:
                        progress[epoch_num] = progress_dict
                elif record.name == "ABORT":
                    logger.log(logging.WARN, "ABORT ACKNOWLEDGED!!!!!!")
                    abort_ack = True
            else:
                running = False
        message = {'logs': logs, 'progress': progress, 'epoch': epoch, 'abort_ack': abort_ack, 'gpu_load': gpu_load}
        if len(logs) > 0 or len(progress.keys()) > 0 or abort_ack:
            message_str = json.dumps(message)
            async_to_sync(channel_layer.group_send)('training_data', {'type': 'send_job_data', 'job_name': job_name, 'text': message_str})
        return (i, j)