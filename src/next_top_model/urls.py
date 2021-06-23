"""next_top_model URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import atexit
from next_top_model.util import check_celery, kill_celery
from django.contrib import admin
from django.urls import include, path
from .settings import GPUS
from pages.views import home_view

urlpatterns = [
    path('', home_view, name='home'),
    path('admin/', admin.site.urls),
    path('projects/', include('projects.urls')),
    path('jobs/', include('jobs.urls')),
    path('graph/', include('graph.urls')),
    path('activities/', include('activities.urls')),
    path('accounts/', include('django.contrib.auth.urls'))
]

# one time startup

celery_beat_pid, celery_default_worker_pid, celery_job_worker_pid = check_celery(GPUS)
if celery_beat_pid is not None and celery_default_worker_pid is not None and celery_job_worker_pid is not None:
    @atexit.register
    def end_celery():
        pass
        kill_celery(celery_beat_pid, celery_default_worker_pid, celery_job_worker_pid)