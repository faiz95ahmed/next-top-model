# next-top-model
Model Training (and Scheduling), Benchmarking, Visualisation

pip install using requirements.txt

cd to src directory and run the following commands in seperate terminals:

```
python3 manage.py runserver
celery -A next_top_model beat -l INFO
celery -A next_top_model worker -n default_worker -Q default -l INFO
celery -A next_top_model worker -n jobs_worker -c NUM_WORKERS -Q jobs -l INFO
```

## TODO:
* start celery beat & workers with server
* GPU usage monitoring
* 1 worker per GPU:
    * to measure GPU usage of training instances for better resource/power usage reporting in papers etc.
    * Also useful in optimising training scripts to be more GPU bound (and less bottlenecked by other things)
* Job Scheduling
* Auto Stopping and restarting around schedules
* Benchmarks, Visualisations, Tables:
    * Export table as LaTeX?
    * Auto generate Table and Figure captions?
    * Export as LaTeX float?

Not really relevant to my project, but could be useful to pick up after I submit my project:
* Compartmentalise Projects and MLModels better
* Showing past logs on the web interface
* Security Concerns
* Better Authentication of Projects, Jobs etc.
* Cosmetic Changes
* Fixing Links
* Testing Suite

## Painful Errors:

https://stackoverflow.com/questions/66960899/django-channels-error-when-attempting-to-serve-static-files-with-devserver