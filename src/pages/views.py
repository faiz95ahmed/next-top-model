from django.http import HttpResponse
from django.shortcuts import redirect

# Create your views here.
def home_view(request, *args, **kwargs):
    return redirect('graph:graph')