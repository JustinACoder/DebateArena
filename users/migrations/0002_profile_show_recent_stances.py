# Generated by Django 5.0.4 on 2024-07-27 16:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='show_recent_stances',
            field=models.BooleanField(default=True),
        ),
    ]