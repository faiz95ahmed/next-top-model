#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import atexit
import os
import sys
from next_top_model.util import start_celery, kill_all_celery, kill_celery
import json

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'next_top_model.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    args = sys.argv
    if args[1] == "runserver":
        # one time startup
        kill_all_celery()
        with open("config.json", "r") as f:
            num_gpus = len(json.loads(f.read())["gpus"])
        celery_pids = start_celery(num_gpus)
        atexit.register(kill_celery, celery_pids)
    execute_from_command_line(args)

if __name__ == '__main__':
    main()