from django.contrib.auth.models import User
from django.db import models
from django.db.models.deletion import CASCADE
from django.urls.base import reverse
# from projects.models import MLModel

# Create your models here.
class Job(models.Model):
    mlmodel     = models.ForeignKey('projects.MLModel', on_delete=CASCADE, null=False, blank=False)
    command     = models.TextField(null=False, blank=False)
    auth_users  = models.ManyToManyField(User, blank=False) # need to add permissions - read (list/detail & create jobs), create (to create subprojects or mlmodels), update&delete (to update&delete)
    order       = models.IntegerField(default=0)
    from_dict   = models.TextField(null=False, default='', blank=True)
    active      = models.BooleanField(default=False)

    def get_absolute_url(self):
        return reverse("jobs:job-detail", kwargs={"id": self.id})

    def get_delete_url(self):
        return reverse("jobs:job-delete", kwargs={"id": self.id})