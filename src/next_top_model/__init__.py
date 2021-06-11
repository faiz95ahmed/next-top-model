from .celery import app as celery_app, add_next_job
from .settings import GPUS

__all__ = ['celery_app']
