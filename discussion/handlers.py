from channels.db import database_sync_to_async
from django.db.models import Q

from discussion.forms import MessageForm
from discussion.models import Discussion
from ProjectOpenDebate.consumers import get_user_group_name


@database_sync_to_async
def save_message_to_db(user, discussion_id, text):
    messageForm = MessageForm({'text': text})

    if messageForm.is_valid():
        messageForm.instance.discussion_id = discussion_id
        messageForm.instance.author = user
        messageForm.save()
        return True
    else:
        return False


async def new_message_handler(consumer, data):
    """
    Handler for new messages. It saves the message to the database and sends it to all participants in the discussion.

    :param consumer: The consumer that received the message
    :param data: The data of the message
    """
    discussion_id = data.get('discussion_id')
    message = str(data.get('message', ''))
    if not isinstance(discussion_id, int) or not message.strip():
        await consumer.send_json({'status': 'error', 'message': 'Missing discussion_id or message'})
        return

    # Get the user from the scope
    user = consumer.scope['user']

    # check that the user is a participant in the discussion
    try:
        discussion = await database_sync_to_async(Discussion.objects.get)(
            Q(participant1=user) | Q(participant2=user),
            id=discussion_id
        )
    except Discussion.DoesNotExist:
        await consumer.send_json({'status': 'error', 'event_type': 'discussion.new_message',
                                  'message': 'You are not a participant in this discussion'})
        return

    # save the message to the database
    is_valid_message = await save_message_to_db(user, discussion_id, message)

    # Send error message if the message is invalid
    if not is_valid_message:
        await consumer.send_json(
            {'status': 'error', 'event_type': 'discussion.new_message', 'message': 'Invalid message'})
        return

    # Send the message to all participants in the discussion
    participants_ids = [discussion.participant1_id, discussion.participant2_id]
    for participant_id in participants_ids:
        user_group_name = get_user_group_name(participant_id)
        await consumer.channel_layer.group_send(
            user_group_name,
            {
                'status': 'success',
                'event_type': 'discussion.new_message',
                'type': 'send.json',
                'data': {
                    'discussion_id': discussion_id,
                    'sender_id': user.id,
                    'sender': user.username,
                    'message': message,
                }
            }
        )


config = {
    'new_message': new_message_handler,
}
