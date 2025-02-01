from datetime import datetime

from django.conf import settings
from django.db import models
from django.db.models.functions import Coalesce
from django.dispatch import receiver
from django.template.loader import render_to_string

from ProjectOpenDebate.consumers import get_user_group_name
from debate.models import Debate
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models.signals import post_save

from discussion.deletion import SET_WITH


def get_previous_message(read_checkpoint):
    """
    Given a ReadCheckpoint, this will return the previous message that was created before the current last_read_message.

    :param read_checkpoint: ReadCheckpoint
    :return: The previous message that was created before the current last_read_message
    """
    # Return the latest message that was created before the current last_read_message
    # If this is the first message, this will return None which will indicate that the user has read no messages
    return Message.objects.filter(
        discussion=read_checkpoint.discussion, created_at__lt=read_checkpoint.created_at
    ).order_by('-created_at').first()


class Discussion(models.Model):
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE)
    participant1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name='p1_discussion_set')
    participant2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name='p2_discussion_set')
    is_archived_for_p1 = models.BooleanField(default=False)
    is_archived_for_p2 = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_from_invite(self):
        return hasattr(self, 'inviteuse')

    def create_read_checkpoints(self):
        """
        Create ReadCheckpoints for both participants of the discussion.
        """
        ReadCheckpoint.objects.create(discussion=self, user=self.participant1)
        ReadCheckpoint.objects.create(discussion=self, user=self.participant2)

    def add_discussion_to_participants_list_live(self, as_unread=True):
        # Get current channel layer
        channel_layer = get_channel_layer()

        # Add the is_unread flag to the discussion
        self.is_unread = as_unread

        # Render discussion to send to the participants
        discussion_html = render_to_string('discussion/discussion.html', context={'discussion': self})

        for participant_id in [self.participant1_id, self.participant2_id]:
            user_group_name = get_user_group_name('DiscussionConsumer', participant_id)

            # TODO: when getting participant usernames and debate titles, we are making additional queries to the database.
            #   The problem is that where we call notify_participants() we usually already have the necessary information.
            #   This isn't a big problem, but its not optimal.
            #   We could pass the necessary information as arguments to notify_participants() instead.
            #   However, it would probably make it less readable.
            async_to_sync(channel_layer.group_send)(
                user_group_name,
                {
                    'status': 'success',
                    'event_type': 'new_discussion',
                    'type': 'send.json',
                    'data': {
                        'discussion_id': self.id,
                        'from_invite': self.is_from_invite,
                        'html': discussion_html,
                    }
                }
            )

    def is_archived_for(self, user):
        if user == self.participant1:
            return self.is_archived_for_p1
        elif user == self.participant2:
            return self.is_archived_for_p2
        else:
            raise ValueError("User is not a participant in the discussion")

    def __str__(self):
        return f"Discussion between {self.participant1} and {self.participant2} on \"{self.debate.title}\""


class Message(models.Model):
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # To quickly get the latest messages in a discussion
            models.Index(fields=['discussion', '-created_at']),
        ]

    def __str__(self):
        return f"Message {self.id} by {self.author} in discussion on \"{self.discussion.debate.title}\""


class DiscussionRequest(models.Model):
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stance_wanted = models.BooleanField()
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request by {self.requester} for debate \"{self.debate.title}\""


class ReadCheckpoint(models.Model):
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    last_message_read = models.ForeignKey(Message, on_delete=SET_WITH(get_previous_message),
                                          null=True)  # null=True because the user might not have read any messages yet
    read_at = models.DateTimeField(null=True)  # null=True because the user might not have read any messages yet

    # If last_message_read is None and read_at is None, the user has not even opened the discussion yet
    # If last_message_read is None and read_at is not None, the user has opened the discussion (but there were no messages)
    # If last_message_read and read_at are not None, the user has read the discussion up to last_message_read at read_at
    # Note: read_at shouldn't be None if last_message_read is not None (TODO: enforce somehow?)

    class Meta:
        unique_together = ('discussion', 'user')
        indexes = [
            # To quickly get the checkpoint for a user in a discussion
            models.Index(fields=['discussion', 'user']),
        ]

    def read_messages(self):
        """
        Update the ReadCheckpoint to indicate that the user has read the latest messages.

        :return: The number of messages that were read
        """
        last_message_read_created_at = self.last_message_read.created_at if self.last_message_read else datetime.min

        # Get the new last_message_read_id along with the number of messages that were read
        unread_messages = self.discussion.message_set.filter(created_at__gt=last_message_read_created_at)
        num_messages_read = unread_messages.count()

        if num_messages_read == 0:
            # if read_at is not set, this means that we have opened the discussion for the first time
            # Therefore, we set read_at to the current time
            if self.read_at is None:
                self.read_at = datetime.now()
                self.save()
            return 0

        # Update the ReadCheckpoint
        self.read_until(unread_messages.order_by('-created_at').first())

        return num_messages_read

    def read_until(self, message):
        """
        Set the message as the latest message read by the user.

        :param message: Message
        """
        self.last_message_read = message
        self.read_at = datetime.now()
        self.save()

    def __str__(self):
        return f"ReadCheckpoint for {self.user} in discussion on \"{self.discussion.debate.title}\""
