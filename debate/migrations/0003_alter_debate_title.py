# Generated by Django 5.0.4 on 2024-07-06 12:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('debate', '0002_debate_slug_alter_debate_title'),
    ]

    operations = [
        migrations.AlterField(
            model_name='debate',
            name='title',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
