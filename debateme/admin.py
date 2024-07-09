from django.contrib import admin

from debateme.models import Invite, InviteUse

admin.site.register([Invite, InviteUse])
