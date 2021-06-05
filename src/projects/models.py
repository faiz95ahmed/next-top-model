from django.db import models
from django.db.models.deletion import CASCADE
from django.contrib.auth.models import User
from django.urls import reverse
from jobs.models import Job

class Project(models.Model):
    title       = models.CharField(max_length=30, blank=False, null=False, unique=True)
    description = models.TextField()
    path        = models.TextField(blank=False, null=True)
    auth_users  = models.ManyToManyField(User, blank=False) # need to add permissions - read (list/detail & create jobs), create (to create subprojects or mlmodels), update&delete (to update&delete)
    parent      = models.ForeignKey('self', on_delete=CASCADE, null=True, blank=True)

    def get_absolute_url(self):
        return reverse("projects:project-detail", kwargs={"id": self.id})

    def get_delete_url(self):
        return reverse("projects:project-delete", kwargs={"id": self.id})

    def get_create_url(self):
        # print(reverse("projects:project-create-child", kwargs={"id": self.id}))
        return reverse("projects:project-create-child", kwargs={"id": self.id})
    
    def get_mlmodel_create_url(self):
        return reverse("projects:project-create-mlmodel", kwargs={"id": self.id})

    # def get_update_url(self):
    #     return reverse("projects:project-update", kwargs={"id": self.id})

    @property
    def get_fq_path(self):
        if self.parent is None:
            return [self.path, self.title]
        else:
            return self.parent.get_fq_path + [self.title]
    
    @property
    def get_ancestors(self):
        a = self.get_ancestors_and_self()[:-1]
        print(a)
        return a
    
    def get_ancestors_and_self(self):
        if self.parent is None:
            return [self.title]
        else:
            return self.parent.get_ancestors_and_self() + [self.title]
    
    @property
    def path_full(self):
        return "/".join(self.get_fq_path).replace(" ", "_")

class MLModel(models.Model):
    title        = models.CharField(max_length=30, blank=False, null=False, unique=True)
    description  = models.TextField()
    auth_users   = models.ManyToManyField(User, blank=False) # need to add permissions - read (list/detail & create jobs), create (to create subprojects or mlmodels), update&delete (to update&delete)
    parent       = models.ForeignKey(Project, on_delete=CASCADE, null=False, blank=False)
    model_name   = models.TextField(null=False, blank=False)
    preproc_name = models.TextField(null=False, blank=False)
    data_path    = models.TextField(null=False, blank=False)

    def get_absolute_url(self):
        return reverse("projects:mlmodel-detail", kwargs={"id": self.id})
    
    def get_delete_url(self):
        return reverse("projects:mlmodel-delete", kwargs={"id": self.id})

    def get_create_url(self):
        return reverse("projects:job-create", kwargs={"id": self.id})
    
    @property
    def get_fq_path(self):
        if self.parent is None:
            return [self.path, self.title]
        else:
            return self.parent.get_fq_path + [self.title]
    
    @property
    def get_ancestors(self):
        return self.parent.get_ancestors_and_self()
       
    @property
    def path_full(self):
        return "/".join(self.get_fq_path).replace(" ", "_")

    @property
    def has_job(self):
        return self.job is not None

    @property
    def job(self):
        qset = Job.objects.filter(mlmodel=self)
        if len(qset) > 0:
            return qset[0]
        else:
            return None
