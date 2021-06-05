from django import forms
from .models import Job

class JobCreateForm(forms.ModelForm):
    parent_name = None
    class Meta:
        model = Job
        fields = ['command', 'from_dict']