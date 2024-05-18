from django.contrib import admin
from .models import Debate, Comment, Stance

admin.site.register([Debate, Comment, Stance])
