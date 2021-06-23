from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import redis
from next_top_model.settings import REDIS_PORT

_redis = redis.Redis(host = 'localhost', port = REDIS_PORT, db = 0)
# Create your views here.
@login_required(login_url='/accounts/login/')
def index(request):
    return render(request, 'realtime_graph.html')

@login_required(login_url='/accounts/login/')
def abort(request):
    if request.method == 'GET':
        job_name = "job_" + request.GET['job_id']
        _redis.lpush(job_name + "_abort", "ABORT")
        return HttpResponse("Aborting!")
    else:
        return HttpResponse("Improper Abort Request!")

