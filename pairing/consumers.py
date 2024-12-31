import asyncio

from channels.db import database_sync_to_async
from django.db import transaction
from django.template.loader import render_to_string

from ProjectOpenDebate.consumers import CustomBaseConsumer, get_user_group_name
from debate.models import Debate
from pairing.models import PairingRequest, PairingMatch


class PairingConsumer(CustomBaseConsumer):
    """
    This consumer handles the WebSocket connection for pairing users together.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.wait_then_pair_coroutine = None

    async def receive_json(self, content, **kwargs):
        """
        Receives a JSON message from the client and processes it.
        Note: all the data here is untrusted, so we should validate it before processing it.

        :param content: The JSON message from the client
        :param kwargs: Additional arguments
        """
        # Get the data from the content
        data = content.get('data', {})

        # check that we have an integer pairing_request_id and an event_type
        pairing_request_id = data.get('pairing_request_id')
        event_type = str(content.get('event_type', ''))
        if not isinstance(pairing_request_id, int) or not event_type:
            await self.send_json({'status': 'error', 'message': 'Missing pairing_request_id or event_type'})
            return

        # Get the user from the scope
        user = self.scope['user']

        # Process the atomic events without a retrieval of the pairing request since this will be done
        # atomically in the methods
        if event_type == 'request_pairing':
            await self.request_pairing(user, data.get('debate_id'))
            return
        elif event_type == 'start_search':
            await self.start_active_search(user)
            return
        elif event_type == 'cancel':
            await self.cancel_pairing_request(user)
            return

        # Get the active pairing request for the user
        pairing_request = await self.get_pairing_request(user)

        if not pairing_request:
            return

        if event_type == 'keepalive':
            pairing_request.update_keepalive()
        else:
            await self.send_json({'status': 'error', 'message': 'Invalid event_type'})

    async def get_pairing_request(self, user, for_update=False):
        """
        Gets the active pairing request for the user.
        """
        pairing_request = await database_sync_to_async(PairingRequest.objects.get_current_request)(user,
                                                                                                   for_update=for_update)

        if not pairing_request:
            await self.send_json({'status': 'error', 'message': 'You do not have an active pairing request'})

        return pairing_request

    async def wait_then_pair(self, pairing_match):
        """
        Waits for a few seconds before completing the pairing.
        """
        try:
            await asyncio.sleep(3.5)

            with transaction.atomic():
                await database_sync_to_async(pairing_match.complete_pairing)()

                # Notify the users that the pairing has been completed
                await self.notify_paired_redirect(pairing_match)

        except asyncio.CancelledError:
            return

    async def start_active_search(self, user):
        """
        Starts the active search for a pairing request.

        For now, starting the active search will also try to find a match for the pairing request.
        In the future, we might want to first activation the search and then wait a bit to ensure that
        we make a good match based on things such as ELO, region, etc.
        """
        with transaction.atomic():
            # Get the active pairing request
            pairing_request = await self.get_pairing_request(user, for_update=True)

            if not pairing_request:
                return

            if pairing_request.status != PairingRequest.Status.IDLE:
                return

            # Switch the status of the pairing request to active
            await database_sync_to_async(pairing_request.switch_status)(PairingRequest.Status.ACTIVE)

            # Get the best match for the pairing request
            best_match = await database_sync_to_async(PairingRequest.objects.get_best_match)(pairing_request,
                                                                                             for_update=True)

            # Check if the best match was found
            if best_match:
                # Create a match
                pairing_match = await database_sync_to_async(PairingMatch.objects.create_match)(pairing_request,
                                                                                                best_match)

        # Outside the atomic block
        if best_match:
            # Notify the users that a match has been found
            await self.notify_match_found(pairing_request, best_match)

            # Create the task
            self.wait_then_pair_coroutine = asyncio.create_task(self.wait_then_pair(pairing_match))
        else:
            await self.notify_start_search(pairing_request)

    async def notify_start_search(self, pairing_request):
        """
        Notifies the user that the active search has started.
        """
        # Get the user group name
        user_group_name = get_user_group_name(self.__class__.__name__, pairing_request.user_id)

        # Notify the user that the active search has started
        await self.channel_layer.group_send(
            user_group_name,
            {
                'status': 'success',
                'type': 'send.json',
                'event_type': 'start_search',
            }
        )

    async def notify_match_found(self, pairing_request, best_match):
        """
        Notifies the two users that a match has been found and pairs them together.
        """
        # Notify the users that a match has been found
        for _pairing_request in [pairing_request, best_match]:
            user = await database_sync_to_async(_pairing_request.user)()
            group_name = get_user_group_name(self.__class__.__name__, user.id)

            await self.channel_layer.group_send(
                group_name,
                {
                    'status': 'success',
                    'type': 'send.json',
                    'event_type': 'match_found',
                }
            )

    @transaction.atomic
    async def cancel_pairing_request(self, user):
        """
        Cancels the pairing request. The whole process is atomic to ensure that the pairing request
        is not matched while it is being cancelled.
        """
        # Get the active pairing request
        pairing_request = await self.get_pairing_request(user, for_update=True)

        if not pairing_request:
            return

        # If the pairing request is active/idle, just delete it
        if pairing_request.status in [PairingRequest.Status.ACTIVE, PairingRequest.Status.IDLE]:
            await self.notify_cancelled(pairing_request)
            pairing_request.adelete()
            return
        # If the pairing request is in match found status, we need to cancel the match
        elif pairing_request.status == PairingRequest.Status.MATCH_FOUND:
            self.wait_then_pair_coroutine.cancel()

            # Retrieve the matched pairing request
            matched_pairing_request = await database_sync_to_async(pairing_request.pairingmatch.get_other_request)(pairing_request)

            # Switch the status of the pairing request to active
            # Note: we know it is an active search since a passive search directly goes to paired status
            #       without go through the match found status. Therefore, we can assume that the status
            #       was active before the match was found.
            await database_sync_to_async(pairing_request.switch_status)(PairingRequest.Status.ACTIVE)
            # TODO: in the future, if we allow active to passive match, we need to switch the statys back to
            #       the original status which might be active or passive here. For now, we will assume that
            #       the status was active before the match was found.
            await database_sync_to_async(matched_pairing_request.switch_status)(PairingRequest.Status.ACTIVE)

            # Notify the users that the match has been cancelled
            await self.notify_cancelled(pairing_request)
            await self.notify_cancelled(pairing_request, matched_pairing_request.user_id)

            # Delete the pairing match and the pairing request
            await pairing_request.pairingmatch.adelete()
            await pairing_request.adelete()
        else:
            await self.send_json({'status': 'error', 'message': 'Invalid status for cancelling pairing request'})

    async def notify_cancelled(self, cancelled_pairing_request, user_id=None):
        """
        Notifies the user that the pairing request has been cancelled.
        If you provide a user_id, it will be used instead of the pairing request's user ID.
        This is useful to notify the other user in the pairing.
        """
        # Get the user group name
        user_id = user_id or cancelled_pairing_request.user_id
        user_group_name = get_user_group_name(self.__class__.__name__, user_id)

        # Notify the user that the pairing request has been cancelled
        await self.channel_layer.group_send(
            user_group_name,
            {
                'status': 'success',
                'type': 'send.json',
                'event_type': 'cancel',
                'data': {
                    'from_current_user': user_id == cancelled_pairing_request.user_id
                }
            }
        )

    async def notify_paired_redirect(self, pairing_match):
        """
        Notifies the users that the pairing has been completed and redirects them to the discussion.
        """
        for pairing_request in [pairing_match.pairing_request_1, pairing_match.pairing_request_2]:
            await self.redirect(pairing_request.user_id, 'specific_discussion', discussion_id=pairing_match.related_discussion_id)

    async def request_pairing(self, user, debate_id):
        """
        Requests a pairing for the user in the specified debate.
        """
        debate = await Debate.objects.filter(id=debate_id).first()

        with transaction.atomic():
            # Check if the user already has an active pairing request
            pairing_request = await database_sync_to_async(PairingRequest.objects.get_current_request)(user)

            if pairing_request:
                await self.send_json({'status': 'error', 'message': 'You already have an active pairing request'})
                return

            # Create the pairing request
            await PairingRequest.objects.acreate(user=user, debate=debate)

        # Notify the user that the pairing request has been created
        await self.notify_request_pairing(pairing_request, debate)

    async def notify_request_pairing(self, pairing_request, debate=None):
        """
        Notifies the user that the pairing request has been created.
        If you provide a debate, it will be used instead of querying the pairing request for the debate.
        This is useful when we have the debate object already.
        """
        # Get the user group name
        user_group_name = get_user_group_name(self.__class__.__name__, pairing_request.user_id)

        # Get the pairing request ID
        html = render_to_string(
            'pairing/pairing_header.html',
            {
                'debate': debate or pairing_request.debate
            }
        )

        # Notify the user that the pairing request has been created
        await self.channel_layer.group_send(
            user_group_name,
            {
                'status': 'success',
                'type': 'send.json',
                'event_type': 'request_pairing',
                'data': {
                    'html': html
                }
            }
        )



