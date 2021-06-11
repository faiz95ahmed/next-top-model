import os
from celery import Celery, shared_task
from celery.utils.log import get_task_logger
from kombu import Queue
from django.apps import apps
from .settings import REDIS_PORT, ABORT_PORT, GPUS
import redis
import shlex
import subprocess
import json
import logging

logger = get_task_logger(__name__)
logging.basicConfig(
      level=logging.DEBUG,
      handlers=[logging.FileHandler('/home/faiz/Desktop/next-top-model/log2.log')]
)
logger2 = logging.getLogger('JOBNAME')
_redis = redis.Redis(host = 'localhost', port = REDIS_PORT, db = 0)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'next_top_model.settings')
app = Celery('next_top_model')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.task_queues = (
    Queue('default'),
    Queue('jobs')
)
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
            }
}
for gpu in GPUS:
    app.conf.beat_schedule['workslot_{}'.format(str(gpu))] = {
                'task': 'next_top_model.graph.tasks.get_logs',
                'schedule': 3.0,
                'options': {
                    'queue': 'default'
                },
                'args': (gpu,)
            }

@shared_task(name='do_job')
def do_job(job_id: int):
    Job = apps.get_model('jobs', 'Job')
    job_name = "job_{}".format(str(job_id))
    curr_job = Job.objects.get(id=job_id)
    # get job data
    gpu_id = curr_job.gpu
    # clean job data
    command = curr_job.get_command(str(REDIS_PORT), str(ABORT_PORT + gpu_id))
    logger2.log(logging.INFO, command)
    # enact command (blocking)
    _ = subprocess.run(shlex.split(command))
    # delete log queue
    _redis.delete(job_name)
    # mark job as complete, and inactive
    curr_job.active=False; curr_job.complete=True
    curr_job.save()

@shared_task(name='add_next_job')
def add_next_job():
    # select least utilised gpu
    gpu_id = 0
    Job = apps.get_model('jobs', 'Job')
    next_job = Job.objects.filter(active=False, complete=False).order_by('order').first()
    if next_job is not None:
        logger.debug('Adding new job %d', next_job.id)
        next_job.active=True
        next_job.gpu=gpu_id
        next_job.save()
        # add job to jobs queue
        app.send_task('do_job', args=(next_job.id,), options={'queue': 'jobs'})
    else:
        logger.debug('No job found')

