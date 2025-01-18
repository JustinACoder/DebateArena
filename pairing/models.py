from django.contrib.auth import get_user_model
from django.db.models import F, Q, Subquery, OuterRef

from debate.models import Debate, Stance
from django.db import models
from datetime import datetime, timedelta, timezone
from django.conf import settings

from discussion.models import Discussion
from discussion.views import create_discussion_and_readcheckpoints


class PairingRequestManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(
            is_expired=(
                    Q(status=PairingRequest.Status.ACTIVE) &
                    Q(last_keepalive_ping__lt=datetime.now() - timedelta(
                        seconds=settings.PAIRING_REQUEST_EXPIRY_SECONDS))
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

        # Other user stance subquery
        other_user_stance = Subquery(
            Stance.objects.filter(
                debate=pairing_request.debate,
                user=OuterRef('user')
            ).values('stance')[:1]
        )

        return queryset.annotate(
            other_user_stance=other_user_stance
        ).filter(
            debate=pairing_request.debate,
            status=pairing_request.status,
            desired_stance=pairing_request.debate.get_stance(pairing_request.user),
            other_user_stance=pairing_request.desired_stance,
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

    @property
    def seconds_elapsed_since_creation(self):
        return round((datetime.now(timezone.utc) - self.created_at).total_seconds())

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
    def create_match_found(self, pairing_request_1, pairing_request_2):
        """
        Creates a PairingMatch between the two PairingRequests.
        """
        pairing_request_1.switch_status(PairingRequest.Status.MATCH_FOUND)
        pairing_request_2.switch_status(PairingRequest.Status.MATCH_FOUND)

        # Create the PairingMatch
        # The related_discussion will be created when the PairingMatch is completed
        pairing_match = self.create(
            pairing_request_1=pairing_request_1,
            pairing_request_2=pairing_request_2,
        )

        return pairing_match


class PairingMatch(models.Model):
    pairing_request_1 = models.OneToOneField(PairingRequest, on_delete=models.CASCADE, related_name='pairing_request_1')
    pairing_request_2 = models.OneToOneField(PairingRequest, on_delete=models.CASCADE, related_name='pairing_request_2')
    related_discussion = models.OneToOneField(Discussion, on_delete=models.CASCADE, related_name='related_discussion', null=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = PairingMatchManager()

    def get_debate(self):
        return self.pairing_request_1.debate

    def get_other_request(self, pairing_request, for_update=False):
        if self.pairing_request_1 == pairing_request:
            if for_update:
                return PairingRequest.objects.select_for_update().get(pk=self.pairing_request_2_id)
            else:
                return self.pairing_request_2
        elif self.pairing_request_2 == pairing_request:
            if for_update:
                return PairingRequest.objects.select_for_update().get(pk=self.pairing_request_1_id)
            else:
                return self.pairing_request_1

    def complete_match(self):
        """
        Completes the pairing by switching the status of the PairingRequests to PAIRED.
        It then creates a new Discussion between the two users and sets it as the related_discussion.

        Returns the created Discussion.
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

        return discussion

    def __str__(self):
        return f'PairingMatch(pairing_request_1={self.pairing_request_1}, pairing_request_2={self.pairing_request_2})'
