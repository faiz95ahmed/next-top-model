from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls.base import reverse

# Create your views here.
def home_view(request, *args, **kwargs):
    return redirect(reverse("graph:graph-index"))