from django import forms
from .models import Project, MLModel

class ProjectCreateFormRoot(forms.ModelForm):
    parent_name = None
    class Meta:
        model = Project
        fields = ['title', 'description', 'path']

class ProjectCreateFormChild(forms.ModelForm):
    parent_name = None
    class Meta:
        model = Project
        fields = ['title', 'description']

class MLModelCreateForm(forms.ModelForm):
    parent_name = None
    class Meta:
        model = MLModel
        fields = ['title', 'description', 'model_name', 'preproc_name', 'data_path']