from django.db import models
from django.urls.base import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from os.path import expanduser
import psutil
import re
from subprocess import PIPE
from pathlib import Path

def validate_conda(env_name):
    proc1 = psutil.Popen(['conda', 'info', '--envs'], stdout=PIPE)
    proc2 = psutil.Popen(['tail', "-n", "+3"], stdin=proc1.stdout, stdout=PIPE)
    proc3 = psutil.Popen(['grep', env_name], stdin=proc2.stdout, stdout=PIPE)
    proc1.stdout.close()
    proc2.stdout.close()
    out, _ = proc3.communicate()
    out_strs = str(out, 'utf8').split("\n")
    matched_envs = [re.split(' +', s)[0] for s in out_strs]
    if env_name not in matched_envs:
        raise ValidationError(
            _('%(env_name)s is not a conda environment on this machine'),
            params={'env_name': env_name},
            )

def validate_script(script_path):
    path = Path(script_path)
    if not path.exists():
        raise ValidationError(
            _('%(path)s does not exist'),
            params={'path': script_path},
            )
    if not path.is_file():
        raise ValidationError(
            _('%(path)s is not a file'),
            params={'path': script_path},
            )
    if not script_path.split(".")[-1] == "py":
        raise ValidationError(
            _('%(path)s is not a python script (with a .py extension)'),
            params={'path': script_path},
            )

#home = expanduser("~/next_top_model/activities") 
class ActivityTypes(models.TextChoices):
    TRAIN = 'TRAIN', _('Training')
    TEST = 'TEST', _('Test')

class Activity(models.Model):
    title             = models.CharField(max_length=30, blank=False, null=False, unique=True)
    description       = models.TextField()
    script_path       = models.TextField(validators=[validate_script])# models.FilePathField(path=home, match="[^\.](.+)\.py", recursive=True)
    additional_args   = models.JSONField(null=True, blank=True, verbose_name="Protocol/Benchmark specific arguments (e.g. training data path)")
    job_type          = models.CharField(max_length=5, default=ActivityTypes.TRAIN, choices=ActivityTypes.choices)
    conda_environment = models.TextField(validators=[validate_conda])
    
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Protocol(Activity):
    def save(self, *args, **kwargs):
        self.job_type = ActivityTypes.TRAIN
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("activities:protocol-detail", kwargs={"id": self.id})

    def get_delete_url(self):
        return reverse("activities:protocol-delete", kwargs={"id": self.id})


class Benchmark(Activity):
    def save(self, *args, **kwargs):
        self.job_type = ActivityTypes.TEST
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("activities:benchmark-detail", kwargs={"id": self.id})

    def get_delete_url(self):
        return reverse("activities:benchmark-delete", kwargs={"id": self.id})

