import os
from GPUtil.GPUtil import GPU
from channels import db
import psutil
import signal
from subprocess import DEVNULL
import GPUtil
from django.apps import apps
from jobs.util import JobStatus
from datetime import time, datetime

CELERY_PIDS = {}
SCHEDULE = None

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

def read_schedule(schedule):
    global SCHEDULE
    ts = []
    for d in schedule:
        d_start = d["start"]
        d_end = d["end"]
        d_type = ("type" in d.keys() and d["type"] != "NOT")
        t_start = time(**d_start)
        t_end = time(**d_end)
        ts.append((t_start, t_end, d_type))
    SCHEDULE = Schedule(ts)

class Schedule(object):
    def __init__(self, ts):
        self.ts = ts
    def check_now(self):
        now = datetime.now()
        t_now = time(hour=now.hour, minute=now.minute, second=now.second)
        return self.check_time(t_now)
    def check_time(self, t_now):
        valid = True
        for t_start, t_end, d_type in self.ts:
            if t_end < t_start:
                valid = valid and self.check_one(t_now, t_end, t_start, not d_type)
            else:
                valid = valid and self.check_one(t_now, t_start, t_end, d_type)
        return valid
    def check_one(self, t_now, t_start, t_end, d_type):
        if t_start <= t_now < t_end:
            return d_type
        return not d_type

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

def kill_celery():
    celery_processes = [(k.replace("_", " ").upper(), v) for k, v in CELERY_PIDS.items()]
    for subprocess_name, subprocess_pid in celery_processes:
        end_process(subprocess_name, subprocess_pid)

def kill_all_celery():
    for p in psutil.process_iter():
        if p.name() == 'celery':
            cmdline = p.cmdline()
            projectname_idx = cmdline.index("-A") + 1
            if cmdline[projectname_idx] == "next_top_model":
                p.kill()

def start_celery(num_gpus):
    p_beat = psutil.Popen(["celery", "-A", "next_top_model", "beat", "-l", "INFO", "-f", "celery_beat.log"], stdout=DEVNULL)
    p_job_monitor = psutil.Popen(["celery", "-A", "next_top_model", "worker", "-n", "job_monitor", "-Q", "monitor", "-l", "INFO", "-f", "celery_monitor_worker.log"], stdout=DEVNULL)
    p_default_worker = psutil.Popen(["celery", "-A", "next_top_model", "worker", "-n", "default_worker", "-c", str(num_gpus), "-Q", "default", "-l", "INFO", "-f", "celery_default_worker.log"], stdout=DEVNULL)
    return p_beat.pid, p_default_worker.pid, p_job_monitor.pid

def check_celery(num_gpus):
    print("STARTING CELERY!")
    p_beat, p_default_worker, p_job_monitor = None, None, None
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
                        elif cmdline[name_idx] == "job_monitor":
                            p_job_monitor = p
                    elif "beat" in cmdline:
                        p_beat = p
        if (p_beat is not None) and (p_default_worker is not None) and (p_job_monitor is not None):
            break
    if p_beat is None:
        p_beat = psutil.Popen(["celery", "-A", "next_top_model", "beat", "-l", "INFO", "-f", "celery_beat.log"], stdout=DEVNULL)
        beat_pid = p_beat.pid
    else:
        beat_pid = None
    if p_job_monitor is None:
        p_job_monitor = psutil.Popen(["celery", "-A", "next_top_model", "worker", "-n", "job_monitor", "-Q", "monitor", "-l", "INFO", "-f", "celery_monitor_worker.log"], stdout=DEVNULL)
        job_monitor_pid = p_job_monitor.pid
    else:
        job_monitor_pid = None
    default_worker_pid = None
    if p_default_worker is None:   
        if num_gpus > 0:
            p_default_worker = psutil.Popen(["celery", "-A", "next_top_model", "worker", "-n", "default_worker", "-c", str(num_gpus), "-Q", "default", "-l", "INFO", "-f", "celery_default_worker.log"], stdout=DEVNULL)
            default_worker_pid = p_default_worker.pid
    return beat_pid, default_worker_pid, job_monitor_pid

def least_utilised_gpu(GPUS):
    # get all gpus
    all_gpus = set(GPUS)
    # get utilised gpus
    Job = apps.get_model('jobs', 'Job')
    utilised_gpus = [d['gpu'] for d in Job.objects.filter(status=JobStatus.RUNNING).values('gpu')]
    # order by (?mem?) usage
    # deviceIDs = GPUtil.getAvailable(order = 'first', includeNan=False, excludeID=utilised_gpus)
    # TODO URGENT: replace the line below with the commented out line above
    deviceIDs = [g for g in GPUS if g not in utilised_gpus]
    # intersect with all_gpus
    valid_gpus = [g for g in deviceIDs if g in all_gpus]
    # return unutilised GPU with lowest mem usage
    return valid_gpus[0]