from django.contrib.auth.models import User
from django.db import models
from django.db.models.deletion import CASCADE
from django.urls.base import reverse
# from projects.models import MLModel

# Create your models here.
class Job(models.Model):
    mlmodel     = models.ForeignKey('projects.MLModel', on_delete=CASCADE, null=False, blank=False)
    script_loc  = models.TextField(default="")
    script_name = models.TextField(default="")
    test_data   = models.TextField(null=True, blank=True)
    auth_users  = models.ManyToManyField(User, blank=False) # need to add permissions - read (list/detail & create jobs), create (to create subprojects or mlmodels), update&delete (to update&delete)
    order       = models.IntegerField(default=0)
    from_dict   = models.TextField(null=False, default='', blank=True)
    active      = models.BooleanField(default=False)
    complete    = models.BooleanField(default=False)
    job_type    = models.CharField(max_length=10, default='TRAIN')
    conda_environment = models.TextField(null=True)
    gpu         = models.IntegerField(null=True)

    def get_absolute_url(self):
        return reverse("jobs:job-detail", kwargs={"id": self.id})

    def get_delete_url(self):
        return reverse("jobs:job-delete", kwargs={"id": self.id})

    def get_command(self, REDIS_PORT: str="REDIS_PORT", ABORT_PORT: str="ABORT_PORT"):
        job_name = "job_{}".format(str(self.id))
        script_loc = self.script_loc
        if len(script_loc) > 0 and script_loc[-1] != "/":
            script_loc = script_loc + "/"
        script_name = self.script_name.replace(" ", "")
        if len(script_name) > 2 and script_name[-3:] != ".py":
            script_name = script_name + ".py"
        script_path = script_loc + script_name
        job_type = self.job_type
        # form command
        command = "conda run -n {} python3 {} --model {} --hyperparams {} --preproc {}".format(self.conda_environment,
                                                                                               script_path,
                                                                                               self.mlmodel.title,
                                                                                               self.mlmodel.path_full + "/hyperparameters.json",
                                                                                               self.mlmodel.preproc_name)
        if self.job_type == "TRAIN":
            train_options = " --save_dir {} --data {} ".format(self.mlmodel.path_full, self.mlmodel.data_path)
            if self.from_dict is not None:
                checkpoint = " --checkpoint " + self.from_dict
            else:
                checkpoint = ""
            command = command + train_options + checkpoint
        elif job_type == "TEST":
            test_options = " --test_data {}".format(self.test_data)
            command = command + test_options
        command = command + " --redis_port {} --abort_port {} --job_name {}".format(REDIS_PORT, ABORT_PORT, job_name)
        return command
