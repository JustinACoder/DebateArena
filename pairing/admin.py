from django.contrib import admin
from .models import PairingRequest, PairingMatch

admin.site.register([PairingRequest, PairingMatch])
