from pathlib import Path
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import redis
from next_top_model.settings import REDIS_PORT
from jobs.models import Job
import json
_redis = redis.Redis(host = 'localhost', port = REDIS_PORT, db = 0)
# Create your views here.
@login_required(login_url='/accounts/login/')
def index(request):
    # determine which jobs are active
    curr_jobs = Job.objects.filter(active=True)
    active_jobs = []
    for curr_job in curr_jobs:
        try:
            results_file = Path(curr_job.mlmodel.path_full, "results.jsonl")
            with open(results_file, "r") as f:
                lines = [json.loads(l.strip()) for l in f.readlines()]
                for line in lines: print(type(line), line)
                results_str = json.dumps(lines).replace(" ", "")
                # print(results_str)
        except FileNotFoundError:
            results_str = "[]"
        model_name = curr_job.mlmodel.title
        job_name = "job_{}".format(str(curr_job.id))
        active_jobs.append((job_name, model_name, results_str))
    num_jobs = len(active_jobs)
    num_rows = (num_jobs + 1) // 2
    job_data = []
    for i in range(num_rows):
        new_dict = {'left': {
                'job_name': active_jobs[i * 2][0],
                'model_name': active_jobs[i * 2][1],
                'values': active_jobs[i * 2][2]
            }}
        if (i * 2) + 2 > num_jobs:
            new_dict['right'] = None
        else:
            new_dict['right'] = {
                'job_name': active_jobs[(i * 2) + 1][0],
                'model_name': active_jobs[(i * 2) + 1][1],
                'values': active_jobs[(i * 2) + 1][2]
            }
        job_data.append(new_dict)
    dumped_vals = [(job_name, results_str) for job_name, _, results_str in active_jobs]
    job_names = json.dumps([n for n, _ in dumped_vals])
    return render(request, 'graph_base.html', context={'job_data': job_data, 'dumped_vals': json.dumps(dict(dumped_vals)), 'job_names': job_names})

@login_required(login_url='/accounts/login/')
def abort(request):
    if request.method == 'GET':
        job_name = request.GET['button_name'].split("-")[1]
        _redis.lpush(job_name + "_abort", "ABORT")
        return HttpResponse("Aborting!")
    else:
        return HttpResponse("Improper Abort Request!")

