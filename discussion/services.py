from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple, Literal

from django.contrib.auth import get_user_model
from django.db.models import Q, F, BooleanField, When, Case, Value, Window, DateTimeField, Subquery, OuterRef, QuerySet
from django.db.models.functions import Greatest
from django.db.models.functions.window import Lag
from django.shortcuts import get_object_or_404

from discussion.models import Discussion, Message, ReadCheckpoint

User = get_user_model()


class DiscussionService:
    @staticmethod
    def get_discussions_for_user(user: User, filterType: Optional[Literal["active", "archived"]] = None) -> QuerySet[Discussion]:
        """
        Get discussions for a user, filtered by type (all, active, archived).
        Each discussion is annotated with additional fields.
        """
        latest_message = Message.objects.filter(discussion=OuterRef('pk')).order_by('-created_at')[:1]
        readcheckpoint = ReadCheckpoint.objects.filter(discussion=OuterRef('pk'), user=user)[:1]

        # Filter the discussions based on the type
        discussions_filter = Q()
        if filterType:
            look_for_archived = filterType == 'archived'
            discussions_filter = ((Q(is_archived_for_p1=look_for_archived) & Q(participant1=user)) |
                                    (Q(is_archived_for_p2=look_for_archived) & Q(participant2=user)))

        return Discussion.objects.filter(
            Q(participant1=user) | Q(participant2=user),
            discussions_filter
        ).annotate(
            latest_message_text=Subquery(latest_message.values('text')),
            latest_message_created_at=Subquery(latest_message.values('created_at')),
            latest_message_author=Subquery(latest_message.values('author__username')),
            readcheckpoint_read_at=Subquery(readcheckpoint.values('read_at')),
            debate_title=F('debate__title')
        ).annotate(
            recent_date=Greatest(
                'created_at',
                F('latest_message_created_at')
            ),
            is_unread=Case(
                When(
                    Q(readcheckpoint_read_at__isnull=True) |
                    (Q(latest_message_created_at__isnull=False) & Q(
                        latest_message_created_at__gt=F('readcheckpoint_read_at'))),
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField()
            )).select_related('debate', 'inviteuse').order_by('-recent_date')

    @staticmethod
    def get_discussion_detail(discussion_id: int, user: User) -> Discussion:
        """
        Get a specific discussion with additional fields.
        """
        discussion = get_object_or_404(
            Discussion.objects.filter(
                Q(participant1=user) | Q(participant2=user)
            ).select_related('debate', 'participant1', 'participant2'),
            pk=discussion_id
        )

        # Add is_archived_for_current_user
        discussion.is_archived_for_current_user = discussion.is_archived_for(user)
        return discussion

    @staticmethod
    def get_discussion_messages(discussion_id: int, user: User) -> QuerySet[Message]:
        """
        Get messages for a specific discussion with annotations.
        """
        # Verify the user has access to this discussion
        discussion = get_object_or_404(
            Discussion.objects.filter(
                Q(participant1=user) | Q(participant2=user)
            ),
            pk=discussion_id
        )

        # Get messages with annotations
        return discussion.message_set.order_by('-created_at').annotate(
            is_current_user=Case(
                When(author=user, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        )

    @staticmethod
    def get_read_checkpoints(discussion_id: int, user: User) -> QuerySet[ReadCheckpoint]:
        """
        Get the read checkpoints for a discussion for a user.
        """
        discussion = get_object_or_404(
            Discussion.objects.filter(
                Q(participant1=user) | Q(participant2=user)
            ),
            pk=discussion_id
        )

        # Get the read checkpoints
        return discussion.readcheckpoint_set

    @staticmethod
    def create_discussion_and_readcheckpoints(debate, participant1, participant2) -> Discussion:
        """
        Create a discussion between two participants and readcheckpoints.
        """
        args = {
            'debate': debate,
            'participant1': participant1,
            'participant2': participant2
        }
        args = {key + '_id' if isinstance(value, int) else key: value for key, value in args.items()}

        discussion_instance = Discussion.objects.create(**args)
        discussion_instance.create_read_checkpoints()

        return discussion_instance

    @staticmethod
    def set_discussion_archive_status(discussion_id: int, user: User, archive_status: bool) -> Discussion:
        """
        Archive or unarchive a discussion for a user.
        """
        discussion = get_object_or_404(
            Discussion.objects.filter(
                Q(participant1=user) | Q(participant2=user)
            ),
            pk=discussion_id
        )

        # Set the archive status
        if user == discussion.participant1:
            discussion.is_archived_for_p1 = archive_status
        else:
            discussion.is_archived_for_p2 = archive_status

        discussion.save()

        # Add is_archived_for_current_user for response
        # TODO: do we need this actually?
        discussion.is_archived_for_current_user = discussion.is_archived_for(user)
        return discussion

    @staticmethod
    def get_discussion_info(discussion_id: int, user: User) -> Dict[str, Any]:
        """
        Get detailed information about a discussion.
        """
        discussion = get_object_or_404(
            Discussion.objects.filter(
                Q(participant1=user) | Q(participant2=user)
            ).select_related('participant1', 'participant2', 'debate', 'inviteuse'),
            pk=discussion_id
        )

        # Get debate
        debate = discussion.debate

        # Get participants and stances
        if user == discussion.participant1:
            current_user = discussion.participant1
            other_user = discussion.participant2
        else:
            current_user = discussion.participant2
            other_user = discussion.participant1

        current_user_stance = debate.get_stance(current_user)
        other_user_stance = debate.get_stance(other_user)

        # Get message count
        message_count = discussion.message_set.count()

        # Get invite info
        invite_id = discussion.inviteuse.invite.id if discussion.is_from_invite else None

        # Check archived status
        is_archived_for_current_user = discussion.is_archived_for(user)

        # Build response
        return {
            "id": discussion.id,
            "debate_id": debate.id,
            "debate_title": debate.title,
            "participant1_id": discussion.participant1.id,
            "participant1_username": discussion.participant1.username,
            "participant1_stance": current_user_stance if user == discussion.participant1 else other_user_stance,
            "participant2_id": discussion.participant2.id,
            "participant2_username": discussion.participant2.username,
            "participant2_stance": other_user_stance if user == discussion.participant1 else current_user_stance,
            "message_count": message_count,
            "is_from_invite": discussion.is_from_invite,
            "invite_id": invite_id,
            "is_archived_for_current_user": is_archived_for_current_user
        }
