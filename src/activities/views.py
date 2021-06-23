from typing import Any
from jobs.util import JobStatus
from django.shortcuts import get_object_or_404
from .forms import ProtocolCreateForm, BenchmarkCreateForm
from .models import Protocol, Benchmark, ActivityTypes
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, DetailView, ListView, UpdateView, DeleteView
from django.apps import apps
from django.db.models import F
import json

activities = {Protocol: 'protocol', Benchmark: 'benchmark'}
activity_enum = {Protocol: ActivityTypes.TRAIN, Benchmark: ActivityTypes.TEST}

# Top level abstract classes
class ActivityView(LoginRequiredMixin):
    activity_type = None
    activity_view_name = None
    @property
    def template_name(self):
        return '{}/{}_{}.html'.format(activities[self.activity_type], activities[self.activity_type], self.activity_view_name)

class ProtocolView():
    activity_type = Protocol

class BenchmarkView():
    activity_type = Benchmark

# List Views
class ActivityListView(ActivityView, ListView):
    activity_view_name = 'list'
    @property
    def queryset(self):
        return self.activity_type.objects.all()

class ProtocolListView(ProtocolView, ActivityListView): pass
class BenchmarkListView(BenchmarkView, ActivityListView): pass

# Detail Views
class ActivityDetailView(ActivityView, DetailView):
    activity_view_name = 'detail'
    def get_object(self):
        id_ = self.kwargs.get("id")
        return get_object_or_404(self.activity_type, id=id_)

class ProtocolDetailView(ProtocolView, ActivityDetailView): pass
class BenchmarkDetailView(BenchmarkView, ActivityDetailView):
    def get_jobs(self):
        curr_benchmark = self.get_object()
        Job = apps.get_model('jobs', 'Job')
        jobs_with_benchmark = Job.objects.filter(status=JobStatus.FINISHED, benchmark=curr_benchmark).values('id', 'from_dict', 'mlmodel__title')#, 'mlmodel__model_args', 'results')
        """jobs_with_benchmark is supposed to be equivalent to
           SELECT J.id, J.from_dict, M.title #, M.model_args, J.results, 
           FROM Jobs J, Mlmodels M
           WHERE J.mlmodel == M.id AND J.status == "FINISHED" AND J.benchmark == curr_benchmark
        """
        return list(jobs_with_benchmark)

    def get_context_data(self, **kwargs):
        jobs_with_benchmark = self.get_jobs()
        kwargs.update({"jobs_with_benchmark": jobs_with_benchmark})
        kwargs.update({"jobs_with_benchmark_str": json.dumps(jobs_with_benchmark)})
        return super().get_context_data(**kwargs)

# Delete Views
class ActivityDeleteView(LoginRequiredMixin, DeleteView):
    activity_view_name = 'delete'
    def get_object(self):
        id_ = self.kwargs.get("id")
        return get_object_or_404(self.activity_type, id=id_)

    def get_success_url(self):
        return reverse("activities:{}-list".format(activities[self.activity_type]))

class ProtocolDeleteView(ProtocolView, ActivityDeleteView): pass
class BenchmarkDeleteView(BenchmarkView, ActivityDeleteView): pass

# Create Views
class ActivityCreateView(ActivityView, CreateView):
    activity_view_name = 'create'
    def form_valid(self, form):
        candidate = form.save(commit=False)
        candidate.job_type = activity_enum[self.activity_type]      
        candidate.save()
        return CreateView.form_valid(self, form)

class ProtocolCreateView(ProtocolView, ActivityCreateView):
    form_class = ProtocolCreateForm

class BenchmarkCreateView(BenchmarkView, ActivityCreateView):
    form_class = BenchmarkCreateForm


# TODO: Update Views