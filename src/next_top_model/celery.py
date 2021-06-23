import os
from pathlib import Path
from celery import Celery, shared_task
from celery.utils.log import get_task_logger
from kombu import Queue
from django.apps import apps
from .settings import BASE_DIR, REDIS_PORT, GPUS, _redis
from .util import least_utilised_gpu

import shlex
import subprocess
import logging
from jobs.util import JobStatus
import json


logger = get_task_logger(__name__)
logging.basicConfig(
      level=logging.DEBUG,
      handlers=[logging.FileHandler(Path.joinpath(BASE_DIR, 'log2.log'))]
)
logger2 = logging.getLogger('JOBNAME')


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'next_top_model.settings')
app = Celery('next_top_model')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.task_queues = (
    Queue('default', durable=False),
    Queue('jobs')
)

app.conf.worker_prefetch_multiplier = 1
app.conf.task_default_queue = 'default'
app.conf.task_routes = {'do_job': {'queue': 'jobs'},
                        }
app.conf.beat_schedule = {
    'add_next_job': {
                'task': 'add_next_job',
                'schedule': 15.0,
                'options': {
                    'queue': 'default'
                }
            },
    'job_monitor': {
        'task': 'next_top_model.graph.tasks.get_logs',
                'schedule': 5.0,
                'options': {
                    'queue': 'default'
                }
    }
}

@shared_task(name='do_job')
def do_job(job_id: int):
    Job = apps.get_model('jobs', 'Job')
    job_name = "job_{}".format(str(job_id))
    curr_job = Job.objects.get(id=job_id)
    # clean job data
    command = curr_job.get_command(str(REDIS_PORT))
    logger2.log(logging.INFO, command)
    # enact command (blocking)
    _ = subprocess.run(shlex.split(command)) # we should really capture and store the pids
                                             # and run the command in a screen, then detach the screen?
    curr_job = Job.objects.get(id=job_id) # reload job from DB
    if (curr_job.status != JobStatus.PAUSING):
        # mark job as complete, and inactive
        curr_job.status = JobStatus.ENDING
        curr_job.save()
    if curr_job.benchmark is not None:
        # this is a benchmark, read the results from redis and save
        # this should be given from the progress logger, with epoch = None
        Result = apps.get_model('jobs', 'Result')
        x = _redis.blpop(job_name.concat("_result"))
        result_dict = json.loads(x)
        res_obj = Result(job=curr_job, epoch=None, content=result_dict)
        res_obj.save()


@shared_task(name='add_next_job')
def add_next_job():
    # select least utilised gpu
    gpu_id = least_utilised_gpu(GPUS)
    Job = apps.get_model('jobs', 'Job')
    next_job = Job.objects.filter(status=JobStatus.PENDING).order_by('order').first()
    if next_job is None:
        logger.debug('No job found')
    elif gpu_id is None:
        logger.debug('No GPU found')
    else:
        logger.debug('Adding new job %d', next_job.id)
        next_job.status=JobStatus.RUNNING
        next_job.gpu=gpu_id
        next_job.save()
        # add job to jobs queue
        app.send_task('do_job', args=(next_job.id,), options={'queue': 'jobs'})