from collections import defaultdict
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from celery import shared_task
import json
import redis
from next_top_model.settings import REDIS_PORT
from jobs.models import Job, Result, Log
from jobs.util import JobStatus
from datetime import datetime
from django.db.models import Q
import time
from pathlib import Path
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

channel_layer = get_channel_layer()
_redis = redis.Redis(host = 'localhost', port = REDIS_PORT, db = 0) 

def handle_log(job, d, log_objects):
    new_log = {"job":             job,
               "message":         d["msg"],
               "relativeCreated": d["relativeCreated"],
               "log_level":       d["levelno"],
               "time":            datetime.utcfromtimestamp(d["created"])}
    # what about all the exception information? and the msecs field?
    # TODO: capture exception information
    log_objects.append(Log(**new_log))
    new_log.pop("job")
    new_log["relativeCreated"] = "{:10.3f}".format(new_log["relativeCreated"]) # TODO: make this conversion clientside
    new_log["time"] = str(new_log["time"])
    return new_log
    # logs[job.id].append(new_log)

def handle_progress(d, epoch, progress, job):
    progress_dict = json.loads(d["msg"])
    epoch_num = progress_dict["epoch"]
    r_epoch = epoch
    if epoch is None:
        r_epoch = epoch_num
    else:
        r_epoch = max(epoch, epoch_num)
    try:
        series_name = progress_dict["series_name"]
    except Exception as e:
        logger.warn(progress_dict)
        logger.error(e)
        raise e
    if series_name in progress[job.id][epoch_num].keys():
        if progress_dict["progress"] > progress[job.id][epoch_num][series_name]["progress"]:
            progress[job.id][epoch_num][series_name]["progress"] = progress_dict["progress"]
            progress[job.id][epoch_num][series_name]["loss"] = progress_dict["loss"]
    else:
        progress[job.id][epoch_num][series_name] = {"progress": progress_dict["progress"],
                                                    "loss":     progress_dict["loss"]}
    return r_epoch

def handle_empty(job):
    # all redis messages consumed
    if job.status == JobStatus.ENDING:
        # this job has finished ending
        job.status = JobStatus.FINISHED
        job.save()
    return False

def save_to_db(log_objects, progress):
    # save logs to DB
    if len(log_objects) > 0:
        Log.objects.bulk_create(log_objects)
    # save progress to DB
    result_objects = []
    for job_id, epoch2series in progress.items():
        job = Job.objects.get(id=job_id)
        min_epoch = min(epoch2series.keys())
        # check if progress entry for this epoch already exists, updating if necessary
        new_result = epoch2series.pop(min_epoch)
        _, _ = Result.objects.update_or_create(job=job, epoch=min_epoch, defaults={'content': new_result})
        if len(epoch2series.keys()) > 0:
            # add progress entries for remaining epochs
            result_objects.extend([Result(job=job, epoch=e, content=d) for e, d in epoch2series.items()])
    if len(result_objects) > 0:
        Result.objects.bulk_create(result_objects)

def send_data(active_job_ids, model_names, logs, progress, abort_ack):
    # send data down sockets
    all_data = {}
    data_exists = False
    for job_id in active_job_ids:
        job_has_new_data = abort_ack[job_id] or (job_id in logs.keys()) or (job_id in progress.keys())
        data_exists = data_exists or job_has_new_data
        if job_has_new_data:
            all_data[job_id] = {"logs": logs[job_id] if job_id in logs.keys() else [],
                                "progress": progress[job_id] if job_id in progress.keys() else {},
                                "abort_ack": abort_ack[job_id],
                                "model_name": model_names[job_id]}
    if data_exists:
        message = {'type': 'send_job_data', 'all_data': json.dumps(all_data)}
        async_to_sync(channel_layer.group_send)('realtime_data', message)

# TODO: This is not starvation-free. May need to fix this.
@shared_task(name='next_top_model.graph.tasks.get_logs')
def get_logs():
    try:
        running_outer = True
        num_messages_received = 0
        while running_outer:
            active_jobs = Job.objects.filter(Q(status=JobStatus.RUNNING) | Q(status=JobStatus.ENDING) | Q(status=JobStatus.PAUSING))
            round_start = time.time()
            running_outer = False
            log_objects = []
            progress = defaultdict(lambda: defaultdict(dict)) # map of job id -> (map of epoch num -> (map of series name -> (progress and loss)))
            logs = defaultdict(list) # map of job id -> list
            abort_ack = {}
            model_names = {}
            for job in active_jobs:
                job_name = "job_{}".format(str(job.id))
                model_names[job.id] = job.mlmodel.title
                running_inner = True
                epoch = None
                abort_ack[job.id] = False
                while running_inner:
                    x = _redis.lpop(job_name)
                    if x is not None:
                        num_messages_received += 1
                        running_outer = True
                        d = json.loads(x)
                        if d["name"] == "PROGRESS":
                            epoch = handle_progress(d, epoch, progress, job)
                        elif d["name"] == "ABORT":
                            if d["msg"] == "MANUAL":
                                # manual abort
                                pass
                            elif d["msg"] == "SCHEDULED":
                                # scheduled abort
                                reloaded_job = Job.objects.get(id=job.id)
                                save_dir = job.mlmodel.path_full
                                p = Path(save_dir)
                                # search for most recent file with prefix checkpoint_ and extension .pt
                                checkpoint = max([p2 for p2 in p.iterdir() if (p2.suffix == ".py" and p2.name[:11] == "checkpoint_")], key=lambda x:x.stat().st_mtime)
                                reloaded_job.from_dict = checkpoint
                                reloaded_job.status == JobStatus.PENDING
                                reloaded_job.save()
                                _redis.ltrim("job_{}_abort".format(job.id),0, 0)
                            abort_ack[job.id] = True
                        else:
                            logs[job.id].append(handle_log(job, d, log_objects))
                    else:
                        running_inner = handle_empty(job)
            save_to_db(log_objects, progress)
            active_job_ids = [job.id for job in active_jobs]
            send_data(active_job_ids, model_names, logs, progress, abort_ack)
            sleep_time = max(0, time.time() - round_start)
            if sleep_time > 0:
                time.sleep(sleep_time)
        return num_messages_received
    except Exception as e:
        print(e)
        raise e