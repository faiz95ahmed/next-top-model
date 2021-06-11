from django import forms
from .models import Job

class JobTrainCreateForm(forms.ModelForm):
    parent_name = None
    class Meta:
        model = Job
        fields = ['conda_environment', 'script_loc', 'script_name', 'from_dict']

class JobTestCreateForm(forms.ModelForm):
    parent_name = None
    class Meta:
        model = Job
        fields = ['conda_environment', 'script_loc', 'script_name', 'test_data']