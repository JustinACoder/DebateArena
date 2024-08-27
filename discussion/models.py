from django.conf import settings
from django.db import models
from django.template.loader import render_to_string

from ProjectOpenDebate.consumers import get_user_group_name
from debate.models import Debate
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class Discussion(models.Model):
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE)
    participant1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='p1_discussion_set')
    participant2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='p2_discussion_set')
    created_at = models.DateTimeField(auto_now_add=True)

    def add_discussion_to_participants_list_live(self):
        # Get current channel layer
        channel_layer = get_channel_layer()

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
                        'html': discussion_html,
                    }
                }
            )

    def __str__(self):
        return f"Discussion between {self.participant1} and {self.participant2} on \"{self.debate.title}\""


class Message(models.Model):
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message {self.id} by {self.author} in discussion on \"{self.discussion.debate.title}\""


class DiscussionRequest(models.Model):
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stance_wanted = models.BooleanField()
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request by {self.requester} for debate \"{self.debate.title}\""
