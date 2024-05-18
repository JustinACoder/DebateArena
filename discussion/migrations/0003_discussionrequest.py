# Generated by Django 5.0.4 on 2024-05-14 14:07

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('debate', '0002_stance'),
        ('discussion', '0002_rename_datetime_added_message_created_at_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DiscussionRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wants_opposite', models.BooleanField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('debate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='debate.debate')),
                ('requester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requester', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]