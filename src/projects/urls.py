"""projects URL Configuration

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
from django.urls import path
from .views import MLModelCreateView, MLModelDeleteView, MLModelDetailView, ProjectListView, ProjectCreateViewRoot, ProjectCreateViewChild, ProjectDetailView, ProjectUpdateView, ProjectDeleteView
from jobs.views import JobCreateView

app_name = 'projects'
urlpatterns = [
    path ('', ProjectListView.as_view(), name='project-list'),
    path ('create', ProjectCreateViewRoot.as_view(), name='project-create-root'),
    path ('<int:id>/', ProjectDetailView.as_view(), name='project-detail'),
    path ('mlmodel/<int:id>/', MLModelDetailView.as_view(), name='mlmodel-detail'),
    path ('mlmodel/<int:id>/create', JobCreateView.as_view(), name='job-create'),
    path ('<int:id>/create', ProjectCreateViewChild.as_view(), name='project-create-child'),
    path ('<int:id>/create-mlmodel', MLModelCreateView.as_view(), name='project-create-mlmodel'),
    # path ('<int:id>/update/', ProjectUpdateView.as_view(), name='project-update'),
    path ('<int:id>/delete/', ProjectDeleteView.as_view(), name='project-delete'),
    path ('mlmodel/<int:id>/delete/', MLModelDeleteView.as_view(), name='mlmodel-delete'),
]