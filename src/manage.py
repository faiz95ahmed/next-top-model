#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


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

    # TODO: manage auxiliary processes
        # check that the redis-server service is running, get the port number
        # start the celery beat
        # start the two celery workers (1 worker for default and n workers for jobs (n = num GPUs))
    execute_from_command_line(sys.argv)
        # kill celery workers?

if __name__ == '__main__':
    main()
