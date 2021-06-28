import os
from pathlib import Path
from celery import Celery, shared_task
from celery.utils.log import get_task_logger
from kombu import Queue
from django.apps import apps
from .settings import BASE_DIR, REDIS_PORT, GPUS, _redis
from .util import least_utilised_gpu, SCHEDULE

import shlex
import subprocess
import GPUtil   
import logging
from jobs.util import JobStatus
import json
from threading import Thread
import time

logger = get_task_logger(__name__)
logging.basicConfig(
      level=logging.DEBUG,
      handlers=[logging.FileHandler(Path.joinpath(BASE_DIR, 'log2.log'))]
)
logger2 = logging.getLogger('L')


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'next_top_model.settings')
app = Celery('next_top_model')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.task_queues = (
    Queue('default', durable=False),
    Queue('monitor', durable=False)
)

app.conf.worker_prefetch_multiplier = 1
app.conf.task_default_queue = 'default'
app.conf.task_routes = {'job_monitor': {'queue': 'monitor'},
                       }
app.conf.beat_schedule = {
    'add_next_job': {
                'task': 'add_next_job',
                'schedule': 15.0,
            },
    'job_monitor': {
        'task': 'next_top_model.graph.tasks.get_logs',
                'schedule': 5.0,
                'options': {
                    'queue': 'monitor'
                }
    }
}


class Monitor(Thread):
    def __init__(self, delay, gpu_id):
        super(Monitor, self).__init__()
        self.stopped = False
        self.delay = delay # Time between calls to GPUtil
        self.start()
        try:
            self.gpu = [g for g in GPUtil.getGPUs() if g.id==gpu_id][0]
        except IndexError:
            print("This GPU does not exist! ({})".format(gpu_id))
            self.stopped = True
        self.total_usage = 0

    def run(self):
        while not self.stopped:
            self.total_usage += self.gpu.load * self.delay
            time.sleep(self.delay)

    def stop(self):
        self.stopped = True
        


# @shared_task(name='do_job')
def do_job(job_id: int):
    Job = apps.get_model('jobs', 'Job')
    curr_job = Job.objects.get(id=job_id)
    if (curr_job.status!=JobStatus.PENDING):
        return logger.info("job already active")
    curr_job.status=JobStatus.RUNNING
    curr_job.save()
    if SCHEDULE.check_now():
        # clear redis queues
        _redis.ltrim("job_{}".format(job_id),0, 0)
        _redis.ltrim("job_{}_abort".format(job_id),0, 0)
        job_name = "job_{}".format(str(job_id))
        # clean job data
        command = curr_job.get_command()
        logger.log(logging.INFO, command)
        # Instantiate monitor with a 1-second delay between updates
        monitor = Monitor(1)
        # enact command (blocking)
        _ = subprocess.run(shlex.split(command)) # we should really capture and store the pids
                                                 # and run the command in a screen, then detach the screen?
        monitor.stop()
        curr_job = Job.objects.get(id=job_id) # reload job from DB
        if (curr_job.status == JobStatus.RUNNING):
            # this job was manually aborted
            # mark job as complete, and inactive
            curr_job.status = JobStatus.ENDING
            curr_job.save()
        if curr_job.benchmark is not None:
            # this is a benchmark, read the results from redis and save
            # this should be given from the progress logger, with epoch = None
            Result = apps.get_model('jobs', 'Result')
            _, x = _redis.blpop(job_name+ "_result")
            result_dict = json.loads(x)
            result_dict.update({"gpu_usage": monitor.total_usage})
            res_obj = Result(job=curr_job, epoch=None, content=result_dict)
            res_obj.save()

@shared_task(name='add_next_job')
def add_next_job():
    Job = apps.get_model('jobs', 'Job')
    if not SCHEDULE.check_now():
        jobs = Job.objects.filter(status=JobStatus.RUNNING).values('id')
        for job_id in jobs:
            _redis.lpush("job_{}_abort".format(job_id), "SCHEDULED")
        logger.info("INCORRECT TIME TO DO JOB")
        return
    # select least utilised gpu
    gpu_id = least_utilised_gpu(GPUS)
    next_job = Job.objects.filter(status=JobStatus.PENDING).order_by('order').first()
    if next_job is None:
        logger.info('No job found')
    elif gpu_id is None:
        logger.info('No GPU found')
    else:
        logger.info('Adding new job %d', next_job.id)
        # next_job.status=JobStatus.RUNNING
        next_job.gpu=gpu_id
        next_job.save()
        # add job to jobs queue
        do_job(next_job.id)