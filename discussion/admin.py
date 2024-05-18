from django.contrib import admin
from .models import Discussion, Message, DiscussionRequest

admin.site.register([Discussion, Message, DiscussionRequest])
