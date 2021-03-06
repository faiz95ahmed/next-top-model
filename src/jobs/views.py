from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView
from django.views.generic.list import ListView
from django.apps import apps
from django.db.models import Max
from .models import Job
from .forms import JobTestCreateForm, JobTrainCreateForm

MLModel = apps.get_model('projects', 'MLModel')

class JobListView(LoginRequiredMixin, ListView):
    template_name = 'job_list.html'
    @property
    def queryset(self):
        viewable_jobs = Job.objects.filter(auth_users__id=self.request.user.id)
        return viewable_jobs

class JobDetailView(LoginRequiredMixin, DetailView):
    template_name = 'job_detail.html'
    def get_object(self):
        id_ = self.kwargs.get("id")
        obj = get_object_or_404(Job, id=id_)
        return obj

class JobDeleteView(LoginRequiredMixin, DeleteView):
    template_name = 'job_delete.html'
    def get_object(self):
        id_ = self.kwargs.get("id")
        # need to also check if user is correct type
        obj = get_object_or_404(Job, id=id_)
        self.parent = self.obj.parent
        return obj

    def get_success_url(self):
        return self.parent.get_absolute_url()

class JobCreateView(LoginRequiredMixin, CreateView):
    @property
    def queryset(self):
        viewable_jobs = Job.objects.filter(auth_users__id=self.request.user.id).order_by('order')
        return viewable_jobs
    
    def form_valid(self, form):
        candidate = form.save(commit=False)
        candidate.mlmodel = self.mlmodel
        # get highest order (low priority)
        maximum_order_val = Job.objects.aggregate(Max('order'))
        if maximum_order_val['order__max'] is None:
            max_ord = 0
        else:
            max_ord = maximum_order_val['order__max'] + 1000
        candidate.order = max_ord
        candidate.save()
        candidate.auth_users.add(self.request.user)
        return CreateView.form_valid(self, form)

    def get_form(self, *args, **kwargs):
        parent_id = self.request.path.split("/")[-2] # parent id is the parent model
        self.mlmodel = get_object_or_404(MLModel, id=parent_id)
        form = super().get_form(*args, **kwargs)
        form.mlmodel = self.mlmodel
        return form

class JobTrainCreateView(JobCreateView):
    template_name = 'job_train_create.html'
    form_class = JobTrainCreateForm
        
class JobTestCreateView(JobCreateView):
    template_name = 'job_test_create.html'
    form_class = JobTestCreateForm