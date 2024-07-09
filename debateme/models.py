from django.conf import settings
from django.db import models
from django.urls import reverse

from debate.models import Debate
from discussion.models import Discussion


class Invite(models.Model):
    code = models.CharField(max_length=32, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE)

    # TODO: Add invite settings such as max uses, expiry date, etc.

    def __str__(self):
        return f"Invite {self.code} for {self.debate} created by {self.creator}"


class InviteUse(models.Model):
    invite = models.ForeignKey(Invite, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resulting_discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE)  # TODO: make discussion undeletable but rather archived (same for all models for that matter)
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invite {self.invite.code} used by {self.user}"
