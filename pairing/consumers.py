import asyncio

from channels.db import database_sync_to_async
from django.db import transaction
from django.template.loader import render_to_string

from ProjectOpenDebate.consumers import CustomBaseConsumer, get_user_group_name
from debate.models import Debate
from pairing.models import PairingRequest, PairingMatch


class NoCurrentPairingRequestException(Exception):
    def __init__(self, user):
        self.user = user
        super().__init__(f'No current pairing request')


class PairingRequestAlreadyExistsException(Exception):
    def __init__(self, user):
        self.user = user
        super().__init__(f'You already have an active pairing request')


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

        # check that we have an event_type
        event_type = str(content.get('event_type', ''))
        if not event_type:
            await self.send_json({'status': 'error', 'message': 'Missing event_type'})
            return

        # Get the user from the scope
        user = self.scope['user']

        # Process the atomic events without a retrieval of the pairing request since this will be done
        # atomically in the methods
        if event_type == 'request_pairing':
            await self.request_pairing(user, data)
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
            await database_sync_to_async(pairing_request.update_keepalive)()
        else:
            await self.send_json({'status': 'error', 'message': 'Invalid event_type'})

    async def get_pairing_request(self, user, for_update=False):
        """
        Gets the active pairing request for the user.
        """
        pairing_request = await database_sync_to_async(PairingRequest.objects.get_current_request)(user,
                                                                                                   for_update=for_update)

        if not pairing_request:
            await self.send_json({'status': 'error', 'message': 'User does not have an active pairing request'})

        return pairing_request

    @database_sync_to_async
    @transaction.atomic
    def create_match(self, pairing_request, best_match):
        """
        Completes the pairing between the two pairing requests.
        """
        return PairingMatch.objects.create_match(pairing_request, best_match)

    async def wait_then_pair(self, pairing_request, best_match):
        """
        Waits for a few seconds before completing the pairing.
        """
        pairing_match = None
        try:
            await asyncio.sleep(3.5)

            pairing_match = await self.create_match(pairing_request, best_match)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await self.send_json({'status': 'error', 'message': str(e)})
        finally:
            self.wait_then_pair_coroutine = None
            if pairing_match:
                await self.notify_paired_redirect(pairing_match)

    @database_sync_to_async
    @transaction.atomic
    def create_pairing_match_or_fail(self, user):
        """
        Creates a pairing match between the two pairing requests.
        """
        # Retrieve and lock the pairing request
        pairing_request = PairingRequest.objects.get_current_request(user, for_update=True)

        if not pairing_request or pairing_request.status != PairingRequest.Status.IDLE:
            raise NoCurrentPairingRequestException(user)

        # Mark the pairing request as active
        pairing_request.switch_status(PairingRequest.Status.ACTIVE)

        # Get the best match for the pairing request
        best_match = PairingRequest.objects.get_best_match(pairing_request, for_update=True)

        # According to the postgresql documentation,
        # "[...] rows that satisfied the query conditions as of the query snapshot will be locked,
        #  although they will not be returned if they were updated after the snapshot and no longer
        #  satisfy the query conditions"
        # This means that we are guaranteed that the best match is still a valid match if we can retrieve it.
        # Source: https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE

        if not best_match:
            return pairing_request, None

        # Mark both pairing requests as match found
        pairing_request.switch_status(PairingRequest.Status.MATCH_FOUND)
        best_match.switch_status(PairingRequest.Status.MATCH_FOUND)

        return pairing_request, best_match

    async def start_active_search(self, user):
        """
        Starts the active search for a pairing request.

        For now, starting the active search will also try to find a match for the pairing request.
        In the future, we might want to first activation the search and then wait a bit to ensure that
        we make a good match based on things such as ELO, region, etc.
        """
        try:
            pairing_request, best_match = await self.create_pairing_match_or_fail(user)
        except NoCurrentPairingRequestException as e:
            await self.send_json({'status': 'error', 'message': str(e)})
            return

        if not best_match:
            await self.notify_start_search(pairing_request)
        else:
            await self.notify_match_found(pairing_request, best_match)
            self.wait_then_pair_coroutine = asyncio.create_task(self.wait_then_pair(pairing_request, best_match))

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
            group_name = get_user_group_name(self.__class__.__name__, _pairing_request.user_id)

            await self.channel_layer.group_send(
                group_name,
                {
                    'status': 'success',
                    'type': 'send.json',
                    'event_type': 'match_found',
                }
            )

    @database_sync_to_async
    @transaction.atomic
    def cancel_pairing_request_or_fail(self, user):
        """
        Cancels the pairing request for the user.
        If no pairing request is found, it will raise a NoCurrentPairingRequestException.

        It returns a list of (Cancelled PairingRequest, User ID to notify) tuples.
        """
        # Retrieve and lock the pairing request
        pairing_request = PairingRequest.objects.get_current_request(user, for_update=True)

        if not pairing_request:
            raise NoCurrentPairingRequestException(user)

        # Switch the status of the pairing request to idle
        pairing_request.switch_status(PairingRequest.Status.IDLE)

        if pairing_request.status in [PairingRequest.Status.ACTIVE, PairingRequest.Status.IDLE]:
            pairing_request.delete()

            # Object is deleted in DB but not in memory, return it for the notification
            return [(pairing_request, user.id)]
        elif pairing_request.status == PairingRequest.Status.MATCH_FOUND:
            if self.wait_then_pair_coroutine:
                # It's too late to cancel the match, we won't cancel it
                self.wait_then_pair_coroutine.cancel()
                return []

            # Retrieve the matched pairing request
            matched_pairing_request = pairing_request.pairingmatch.get_other_request(pairing_request, for_update=True)

            # Switch the status of the matched pairing request to active
            # Note: we know it is an active search since a passive search directly goes to paired status
            #       without go through the match found status. Therefore, we can assume that the status
            #       was active before the match was found.
            # TODO: in the future, if we allow active to passive match, we need to switch the statys back to
            #       the original status which might be active or passive here. For now, we will assume that
            #       the status was active before the match was found.
            matched_pairing_request.switch_status(PairingRequest.Status.ACTIVE)

            # Delete the pairing match and the pairing request
            pairing_request.pairingmatch.delete()
            pairing_request.delete()

            # Object is deleted in DB but not in memory, return it for the notification
            return [(pairing_request, user.id), (pairing_request, matched_pairing_request.user_id)]

        else:
            raise Exception('Invalid status for cancelling pairing request')

    async def cancel_pairing_request(self, user):
        """
        Cancels the pairing request.
        """
        try:
            notify_list = await self.cancel_pairing_request_or_fail(user)
        except NoCurrentPairingRequestException as e:
            await self.send_json({'status': 'error', 'message': str(e)})
            return

        # Notify the users that the pairing request has been cancelled
        for cancelled_pairing_request, user_id in notify_list:
            await self.notify_cancelled(cancelled_pairing_request, user_id=user_id)

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
            await self.redirect(pairing_request.user_id, 'specific_discussion',
                                discussion_id=pairing_match.related_discussion_id)

    @database_sync_to_async
    @transaction.atomic
    def create_pairing_request_or_fail(self, user, debate, desired_stance):
        """
        Creates a pairing request for the user in the specified debate.
        If the user already has an active pairing request, it will raise a PairingRequestAlreadyExistsException.
        """
        # Check if the user already has an active pairing request
        pairing_request = PairingRequest.objects.get_current_request(user, for_update=True)

        if pairing_request:
            raise PairingRequestAlreadyExistsException(user)

        # Create the pairing request
        return PairingRequest.objects.create(user=user, debate=debate, desired_stance=desired_stance)

    async def request_pairing(self, user, data):
        """
        Requests a pairing for the user in the specified debate.
        """
        debate_id = data.get('debate_id')
        desired_stance = data.get('desired_stance')
        if not isinstance(debate_id, int) or desired_stance not in [True, False]:
            await self.send_json({'status': 'error', 'message': 'Missing valid debate_id or desired_stance'})
            return

        try:
            debate = await Debate.objects.aget(id=debate_id)
        except Debate.DoesNotExist:
            await self.send_json({'status': 'error', 'message': 'Debate does not exist'})
            return

        try:
            pairing_request = await self.create_pairing_request_or_fail(user, debate, desired_stance)
        except PairingRequestAlreadyExistsException as e:
            await self.send_json({'status': 'error', 'message': str(e)})
            return

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
