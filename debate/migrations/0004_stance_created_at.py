# Generated by Django 5.0.4 on 2024-07-24 19:23

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('debate', '0003_alter_debate_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='stance',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]