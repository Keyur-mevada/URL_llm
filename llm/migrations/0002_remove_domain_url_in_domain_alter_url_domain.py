# Generated by Django 5.1.6 on 2025-02-13 19:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('llm', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='domain',
            name='url_in_domain',
        ),
        migrations.AlterField(
            model_name='url',
            name='domain',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='urls', to='llm.domain'),
        ),
    ]
