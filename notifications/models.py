from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse

from ProjectOpenDebate.consumers import get_user_group_name


class NotificationType(models.Model):
    name = models.CharField(max_length=255)
    title_template = models.CharField(max_length=255)
    message_template = models.CharField(max_length=2000)
    endnote_template = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class NotificationManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('notification_type')

    def create_new_discussion_notification(self, user_to_notify, other_user_name, discussion_id, debate_title):
        """ Create a new discussion notification for the user. """
        return self.create(
            user=user_to_notify,
            notification_type=NotificationType.objects.get(name='new_discussion'),
            data={
                'debate_title': debate_title,
                'participant_username': other_user_name
            },
            url_name='specific_discussion',
            url_args={'discussion_id': discussion_id}
        )

    def create_bulk_new_discussion_notification(self, users_to_notify, other_user_names, discussion_ids, debate_titles):
        if len(users_to_notify) != len(other_user_names) != len(discussion_ids) != len(debate_titles):
            raise ValueError('The length of the arguments must be the same.')

        notification_type = NotificationType.objects.get(name='new_discussion')

        notifications = []
        for user_to_notify, other_user_name, discussion_id, debate_title in zip(users_to_notify, other_user_names, discussion_ids, debate_titles):
            notifications.append(Notification(
                user=user_to_notify,
                notification_type=notification_type,
                data={
                    'debate_title': debate_title,
                    'participant_username': other_user_name
                },
                url_name='specific_discussion',
                url_args={'discussion_id': discussion_id}
            ))

        return self.bulk_create(notifications)

    def create_new_message_notification(self, user, message):
        return self.create(
            user=user,
            notification_type=NotificationType.objects.get(name='new_message'),
            data={
                'debate_title': message.discussion.debate.title,
                'participant_username': message.author.username
            },
            url_name='specific_discussion',
            url_args={'discussion_id': message.discussion.id}
        )

    def create_accepted_invite_notification(self, invite, invite_use, accepting_user):
        return self.create(
            user=invite.creator,
            notification_type=NotificationType.objects.get(name='accepted_invite'),
            data={
                'debate_title': invite.debate.title,
                'participant_username': accepting_user.username,
            },
            url_name='specific_discussion',
            url_args={'discussion_id': invite_use.resulting_discussion.id}
        )


class Notification(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE)
    data = models.JSONField(default=dict)  # of the form {'arg1': 'abc', 'arg2': 'def'} for "template: {arg1}-{arg2}"
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # There are many ways to store the url of the related object.
    # - Store the url directly as a URLField (contains the domain name and protocol)
    # - Store the url as a CharField (contains the path only) + custom validator
    # - Store the related object through a GenericForeignKey and call get_absolute_url() on it
    #     This is the most robust way because it allows us to change the URL structure of the related object without changing the Notification model
    #     However, it requires an additional query to the database to get the related object. It also increases the complexity of the code.
    #     It also requires the related object to have a get_absolute_url() method. Finally, it requires each notification to be related to an object.
    # - Store both the url pattern name and the arguments to reverse the url
    #     This is a good compromise between the two previous methods. It allows us to change the URL structure without changing the Notification model.
    #     It also allows us to store the URL of the related object without having to store the related object itself.
    #     However, if we change the url pattern name, the link will be broken unless we create a custom migration to update the url pattern name.
    # We will use the last method here. However, we may need to switch in the future if this causes too much trouble.
    url_name = models.CharField(max_length=255, blank=True)
    url_args = models.JSONField(default=dict)

    objects = NotificationManager()

    @property
    def title(self):
        return self.notification_type.title_template.format(**self.data)

    @property
    def message(self):
        return self.notification_type.message_template.format(**self.data)

    @property
    def endnote(self):
        return self.notification_type.endnote_template.format(**self.data)

    @property
    def redirect_url(self):
        return reverse(self.url_name, kwargs=self.url_args) if self.url_name else 'javascript:void(0)'

    def __str__(self):
        return f'Notification for {self.user.username} at {self.created_at}'


@receiver(post_save, sender=Notification)
def send_notification(sender, instance, created, **kwargs):
    """
    Send the notification to the user using the WebSocket.
    """
    if not created:
        return

    # Get current channel layer
    channel_layer = get_channel_layer()

    # Get the user group name
    user_group_name = get_user_group_name('NotificationConsumer', instance.user.id)

    # Render the notification data
    html = render_to_string('notifications/notification.html', {'notification': instance})

    # Send the notification to the user
    async_to_sync(channel_layer.group_send)(
        user_group_name,
        {
            'status': 'success',
            'event_type': 'new_notification',
            'type': 'send.json',
            'data': {
                'notification_id': instance.id,
                'html': html
            }
        }
    )
