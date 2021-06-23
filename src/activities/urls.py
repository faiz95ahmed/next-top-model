"""activities URL Configuration

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
from .views import BenchmarkListView, BenchmarkCreateView, BenchmarkDetailView, BenchmarkDeleteView, ProtocolListView, ProtocolCreateView, ProtocolDetailView, ProtocolDeleteView

app_name = 'activities'
urlpatterns = [
    path ('benchmark', BenchmarkListView.as_view(), name='benchmark-list'),
    path ('benchmark/create', BenchmarkCreateView.as_view(), name='benchmark-create'),
    path ('benchmark/<int:id>/', BenchmarkDetailView.as_view(), name='benchmark-detail'),
    path ('benchmark/<int:id>/delete', BenchmarkDeleteView.as_view(), name='benchmark-delete'),
    path ('protocol', ProtocolListView.as_view(), name='protocol-list'),
    path ('protocol/create', ProtocolCreateView.as_view(), name='protocol-create'),
    path ('protocol/<int:id>/', ProtocolDetailView.as_view(), name='protocol-detail'),
    path ('protocol/<int:id>/delete', ProtocolDeleteView.as_view(), name='protocol-delete')
]
