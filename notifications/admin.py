from django.contrib import admin
from .models import Notification, NotificationType

admin.site.register([Notification, NotificationType])
