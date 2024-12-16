from django.conf import settings
from django.db import models
from django.urls import reverse

from debate.models import Debate
from discussion.models import Discussion
from django.utils.crypto import get_random_string


def generate_code():
    return get_random_string(8)  # TODO: make sure this is unique? Or do we assume it is since it is extremely unlikely


class Invite(models.Model):
    code = models.CharField(max_length=8, unique=True, default=generate_code)
    created_at = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE)

    # TODO: Add invite settings such as max uses, expiry date, etc.

    def get_absolute_url(self):
        return reverse('view_invite', args=[self.code])

    def __str__(self):
        return f"Invite {self.code} for {self.debate} created by {self.creator}"


class InviteUse(models.Model):
    invite = models.ForeignKey(Invite, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resulting_discussion = models.OneToOneField(Discussion, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invite {self.invite.code} used by {self.user}"
