# next-top-model
Model Training (and Scheduling), Benchmarking, Visualisation

pip install using requirements.txt

cd to src directory and run the following command:

```
python3 manage.py runserver
```

## TODO:
* GPU usage monitoring
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
* Tests!

## Painful Errors:

https://stackoverflow.com/questions/66960899/django-channels-error-when-attempting-to-serve-static-files-with-devserver

## Nice trick

To avoid having to actually setup the webserver in a production setting, serve it via an SSH socket. Do the following:

```ssh -L xyz:127.0.0.1:8000 user@server -N -i identity_file```

and navigate to 127.0.0.1:xyz on your local machine to access the interface.