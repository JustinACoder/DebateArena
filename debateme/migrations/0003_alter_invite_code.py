# Generated by Django 5.0.4 on 2024-07-10 04:38

import debateme.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('debateme', '0002_rename_created_invite_created_at_inviteuse'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invite',
            name='code',
            field=models.CharField(default=debateme.models.generate_code, max_length=8, unique=True),
        ),
    ]
