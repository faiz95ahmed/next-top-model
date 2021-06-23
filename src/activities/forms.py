from django import forms
from .models import Protocol, Benchmark

FIELDS = ['title', 'description', 'script_path', 'additional_args', 'conda_environment']

class ProtocolCreateForm(forms.ModelForm):
    parent_name = None
    class Meta:
        model = Protocol
        fields = FIELDS

class BenchmarkCreateForm(forms.ModelForm):
    parent_name = None
    class Meta:
        model = Benchmark
        fields = FIELDS