from django.contrib.auth import get_user_model
from django.db.models import F, Q

from debate.models import Debate
from django.db import models
from datetime import datetime, timedelta
from django.conf import settings

from discussion.models import Discussion
from discussion.views import create_discussion_and_readcheckpoints


class PairingRequestManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(
            is_expired=(
                Q(status=PairingRequest.Status.ACTIVE) &
                Q(last_keepalive_ping__lt=datetime.now() - timedelta(seconds=settings.PAIRING_REQUEST_EXPIRY_SECONDS))
            )
        )

    def get_current_request(self, user, for_update=False):
        queryset = self.select_for_update() if for_update else self
        return queryset.filter(
            user=user,
            status__in=(PairingRequest.Status.ACTIVE, PairingRequest.Status.IDLE, PairingRequest.Status.MATCH_FOUND),
            is_expired=False
        ).first()

    def get_best_match(self, pairing_request, for_update=False):
        queryset = self.select_for_update() if for_update else self
        return queryset.filter(
            debate=pairing_request.debate,
            status=pairing_request.status,
            desired_stance=pairing_request.user.get_stance(pairing_request.debate),
            user__stance_set__debate=pairing_request.debate,
            user__stance_set__stance=pairing_request.desired_stance,
            is_expired=False
        ).exclude(user=pairing_request.user).first()


class PairingRequest(models.Model):
    class Status(models.TextChoices):
        IDLE = 'idle'
        ACTIVE = 'active'
        PASSIVE = 'passive'
        MATCH_FOUND = 'match_found'
        PAIRED = 'paired'

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE)
    desired_stance = models.BooleanField()  # True for "for", False for "against"
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.IDLE)
    last_keepalive_ping = models.DateTimeField(auto_now_add=True)  # doesn't update on save, must be updated manually
    created_at = models.DateTimeField(auto_now_add=True)

    objects = PairingRequestManager()

    def update_keepalive(self):
        """
        Updates the last_keepalive_ping field to the current time.

        This should be called by the client every settings.PAIRING_KEEPALIVE_INTERVAL seconds
        to keep the PairingRequest active.
        """
        self.last_keepalive_ping = datetime.now()
        self.save()

    def switch_status(self, new_status: Status):
        """
        Switches the status of the PairingRequest to the new_status.
        """
        self.status = new_status
        self.save()

    def __str__(self):
        return f'PairingRequest(user={self.user}, debate={self.debate}, status={self.status})'


class PairingMatchManager(models.Manager):
    def create_match(self, pairing_request_1, pairing_request_2, status=PairingRequest.Status.MATCH_FOUND):
        """
        Creates a new PairingMatch between the two PairingRequests.
        """
        # Switch the status of the PairingRequests
        pairing_request_1.switch_status(status)
        pairing_request_2.switch_status(status)

        # Create the PairingMatch
        return self.create(pairing_request_1=pairing_request_1, pairing_request_2=pairing_request_2)

    def get_other_request(self, pairing_request):
        return self.filter(
            Q(pairing_request_1=pairing_request) | Q(pairing_request_2=pairing_request)
        ).exclude(id=pairing_request.id).first()


class PairingMatch(models.Model):
    pairing_request_1 = models.OneToOneField(PairingRequest, on_delete=models.CASCADE, related_name='pairing_request_1')
    pairing_request_2 = models.OneToOneField(PairingRequest, on_delete=models.CASCADE, related_name='pairing_request_2')
    related_discussion = models.OneToOneField(Discussion, on_delete=models.CASCADE, related_name='related_discussion')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = PairingMatchManager()

    def get_debate(self):
        return self.pairing_request_1.debate

    def get_other_request(self, pairing_request):
        if self.pairing_request_1 == pairing_request:
            return self.pairing_request_2
        elif self.pairing_request_2 == pairing_request:
            return self.pairing_request_1

    def complete_pairing(self):
        """
        Completes the pairing by switching the status of the PairingRequests to PAIRED.
        It then creates a new Discussion between the two users and sets it as the related_discussion.
        """
        self.pairing_request_1.switch_status(PairingRequest.Status.PAIRED)
        self.pairing_request_2.switch_status(PairingRequest.Status.PAIRED)

        # Create the Discussion
        discussion = create_discussion_and_readcheckpoints(
            self.pairing_request_1.debate_id,
            self.pairing_request_1.user_id,
            self.pairing_request_2.user_id
        )

        # No need to add to live discussion list since we will redirect the user to the discussion
        # which will automatically add the discussion to the live discussion list

        self.related_discussion = discussion
        self.save()

    def __str__(self):
        return f'PairingMatch(pairing_request_1={self.pairing_request_1}, pairing_request_2={self.pairing_request_2})'
