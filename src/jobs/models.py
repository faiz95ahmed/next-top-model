import json
from django.contrib.auth.models import User
from django.db import models
from django.db.models.deletion import CASCADE
from django.urls import base
from django.urls.base import reverse

from next_top_model.settings import REDIS_PORT # possibility of a circular import here
from django.core.exceptions import ValidationError
from pathlib import Path
from .util import JobStatus

INTEGER_FIELD_MAX = (2**31) - 1 # TODO: is there something like IntegerField.MaxValue that I could use instead?

def to_str_safe(d):
    b = json.dumps(d).encode('utf8')
    ls = []
    for c in b:
        if c == 39:
            ls = ls + [92, 117, 48, 48, 50, 55]
        else:
            ls.append(c)
    return "--json_args" + bytes(ls).decode()

# Create your models here.
class Job(models.Model):
    mlmodel     = models.ForeignKey('projects.MLModel', on_delete=CASCADE, null=False, blank=False)
    auth_users  = models.ManyToManyField(User, blank=False) # need to add permissions - read (list/detail & create jobs), create (to create subprojects or mlmodels), update&delete (to update&delete)
    order       = models.IntegerField(default=INTEGER_FIELD_MAX)
    from_dict   = models.FilePathField(null=True, path=Path.home(), recursive=True, match='checkpoint_(\d)+\.pt',blank=True)
    protocol    = models.ForeignKey('activities.Protocol', on_delete=CASCADE, null=True, blank=True)
    benchmark   = models.ForeignKey('activities.Benchmark', on_delete=CASCADE, null=True, blank=True)
    status      = models.CharField(max_length=8, default=JobStatus.PENDING, choices=JobStatus.choices)
    gpu         = models.IntegerField(null=True)

    # status == RUNNING or ENDING -> there is no other job with status == RUNNING or ENDING with the same gpu
    # TODO: how to model this as a constraint?
    
    def get_absolute_url(self):
        return reverse("jobs:job-detail", kwargs={"id": self.id})

    def get_delete_url(self):
        return reverse("jobs:job-delete", kwargs={"id": self.id})

    @property
    def job_type(self):
        if self.protocol is None:
            return "TEST"
        else:
            return "TRAIN"

    def get_command(self):
        job_name = "job_{}".format(str(self.id))
        is_train = self.protocol is not None
        activity = self.protocol if is_train else self.benchmark
        job_type = 'TRAIN' if is_train else 'TEST'
        script_path = activity.script_path
        conda_env = activity.conda_environment
        activity_args = (activity.additional_args).copy() if activity.additional_args is not None else {}
        model_args = self.mlmodel.model_args
        # using the code below, model args take precedence over activity args
        for k, v in model_args.items():
            activity_args[k] = v
        
        # form command
        base_command = "conda run -n {} python3 {}".format(conda_env, script_path)
        interface_args = "--job_name {} --save_dir {} --redis_port {}".format(job_name,
                                                                              self.mlmodel.path_full,
                                                                              REDIS_PORT)
        additional_args = "--job_type {} --gpu {} {}".format(job_type, self.gpu, to_str_safe(activity_args))                                  
        command = " ".join([base_command, interface_args, additional_args])
        return command

    def clean(self):
        # ensure precisely one of protocol or benchmark is defined
        if (self.protocol is None) == (self.benchmark is None):
            raise ValidationError("Only one of Protocol and Benchmark can be defined!")
        # if benchmark is defined ensure that from_dict is defined
        # if (self.benchmark is not None) and (self.from_dict is None):
        #     raise ValidationError("Need a saved model for benchmarking!")

class Log(models.Model):
    job             = models.ForeignKey(Job, on_delete=CASCADE)
    message         = models.JSONField()
    relativeCreated = models.FloatField()
    log_level       = models.IntegerField() # increments of 10: (0: not set; debug; info; warning; error; 50: critical)
    time            = models.DateTimeField()

class Result(models.Model):
    job     = models.ForeignKey(Job, on_delete=CASCADE)
    epoch   = models.IntegerField(null=True) 
    content = models.JSONField(blank=True, default=dict)
    class Meta:
        unique_together = ('job', 'epoch')