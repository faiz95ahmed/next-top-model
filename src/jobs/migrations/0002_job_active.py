# Generated by Django 3.1.2 on 2021-06-05 18:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='active',
            field=models.BooleanField(default=False),
        ),
    ]
