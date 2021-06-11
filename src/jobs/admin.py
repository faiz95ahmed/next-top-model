from django.contrib import admin
from .models import Job
from next_top_model.celery import add_next_job
from next_top_model.settings import GPUS


admin.site.register(Job)
# Register your models here.