from django import forms
from django.db import models
from .models import Job

class JobCreateForm(forms.ModelForm):
    parent_name = None

    def get_formfield_callback(self):
        def callback(field):
            if isinstance(field, models.FilePathField):
                return super(field).formfield(**{
                    'path': self.get_path,
                    'match': field.match,
                    'recursive': False,
                    'form_class': forms.FilePathField,
                    'allow_files': field.allow_files,
                    'allow_folders': field.allow_folders,
                })
            return field.formfield()
        return callback

    formfield_callback = get_formfield_callback

    def get_path(self):
        return self.parent.path_full

class JobTrainCreateForm(JobCreateForm):
    class Meta:
        model = Job
        fields = ['protocol', 'from_dict']

class JobTestCreateForm(JobCreateForm):
    class Meta:
        model = Job
        fields = ['benchmark', 'from_dict']