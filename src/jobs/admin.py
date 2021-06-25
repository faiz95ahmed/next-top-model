from django.contrib import admin
from .models import Job, Result, Log
from next_top_model.settings import GPUS


admin.site.register(Job)
admin.site.register(Result)
admin.site.register(Log)
# Register your models here.