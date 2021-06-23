import os
from GPUtil.GPUtil import GPU
import psutil
import signal
from subprocess import DEVNULL
import GPUtil
from django.apps import apps
from jobs.util import JobStatus

def check_redis():
    redis_process = None
    for p in psutil.process_iter():
        if p.name() == 'redis-server':
                redis_process = p
                break
    if redis_process is None:
        raise Exception("redis-server not started!") # start the redis-server here?
    redis_port = int(redis_process.cmdline()[0].split()[-1].split(":")[-1])
    return redis_port

class BoolWrapper(object):
    def __init__(self, x):
        self.x = x

def end_process(name, pid, original_timeout=5):
    def prockill(process, name, boolwrapper):
        print("Killing {}".format(name))
        process.kill()
        boolwrapper.x = False
    timeout = original_timeout
    p = psutil.Process(pid)
    running = BoolWrapper(True)
    signal.signal(signal.SIGINT, lambda x, y: prockill(p, name, running))
    signal.signal(signal.SIGTERM, lambda x, y: prockill(p, name, running))
    while running.x:
        print("Terminating {}, {}s timeout".format(pid, timeout))
        p.terminate()
        try:
            p.wait(timeout=timeout)
        except psutil.TimeoutExpired:
            print("Timeout expired, retrying...")
            timeout *= 2
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

def kill_celery(celery_beat_pid, celery_default_worker_pid, celery_job_worker_pid=None):
    celery_processes = [("CELERY BEAT", celery_beat_pid), ("CELERY DEFAULT WORKER", celery_default_worker_pid)]
    if celery_job_worker_pid is not None:
        celery_processes += [("CELERY JOBS WORKER", celery_job_worker_pid)]
    for subprocess_name, subprocess_pid in celery_processes:
        end_process(subprocess_name, subprocess_pid)

def check_celery(gpus):
    print("STARTING CELERY!")
    p_beat, p_default_worker, p_jobs_worker = None, None, None
    for p in psutil.process_iter():
        if p.name() == 'celery' and p.status != 'zombie':
            cmdline = p.cmdline()
            if len(cmdline) > 0:
                projectname_idx = cmdline.index("-A") + 1
                if p.cwd() == os.getcwd() and cmdline[projectname_idx] == "next_top_model":
                    is_worker = False
                    try:
                        _ = cmdline.index("worker")
                        is_worker = True
                    except ValueError:
                        pass
                    if is_worker:
                        name_idx = cmdline.index("-n") + 1
                        if cmdline[name_idx] == "default_worker":
                            p_default_worker = p
                        elif cmdline[name_idx] == "jobs_worker":
                            p_jobs_worker = p
                    elif "beat" in cmdline:
                        p_beat = p
        if (p_beat is not None) and (p_default_worker is not None) and (p_jobs_worker is not None):
            break
    if p_beat is None:
        p_beat = psutil.Popen(["celery", "-A", "next_top_model", "beat", "-l", "INFO", "-f", "celery_beat.log"], stdout=DEVNULL)
        beat_pid = p_beat.pid
    else:
        beat_pid = None
    if p_default_worker is None:
        p_default_worker = psutil.Popen(["celery", "-A", "next_top_model", "worker", "-n", "default_worker", "-Q", "default", "-l", "INFO", "-f", "celery_default_worker.log"], stdout=DEVNULL)
        default_worker_pid = p_default_worker.pid
    else:
        default_worker_pid = None
    job_worker_pid = None
    if p_jobs_worker is None:   
        if len(gpus) > 0:
            p_jobs_worker = psutil.Popen(["celery", "-A", "next_top_model", "worker", "-n", "jobs_worker", "-c", str(len(gpus)), "-Q", "jobs", "-l", "INFO", "-f", "celery_jobs_worker.log"], stdout=DEVNULL)
            job_worker_pid = p_jobs_worker.pid
    return beat_pid, default_worker_pid, job_worker_pid

def least_utilised_gpu(GPUS):
    # get all gpus
    all_gpus = set(GPUS)
    # get utilised gpus
    Job = apps.get_model('jobs', 'Job')
    utilised_gpus = [d['gpu'] for d in Job.objects.filter(status=JobStatus.RUNNING).values('gpu')]
    # order by (?mem?) usage
    # deviceIDs = GPUtil.getAvailable(order = 'first', includeNan=False, excludeID=utilised_gpus)
    # TODO URGENT: replace the line below with the commented out line above
    deviceIDs = GPUS
    # intersect with all_gpus
    valid_gpus = [g for g in deviceIDs if g in all_gpus]
    # return unutilised GPU with lowest mem usage
    return valid_gpus[0]