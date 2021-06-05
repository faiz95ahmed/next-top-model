# Generated by Django 3.1.2 on 2021-06-05 19:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_job_active'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='job',
            name='checkpoint',
        ),
        migrations.AddField(
            model_name='job',
            name='from_dict',
            field=models.TextField(blank=True, default=''),
        ),
    ]