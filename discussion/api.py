from typing import List, Optional, Literal
from datetime import datetime

from ninja import Router, Schema
from ninja.pagination import paginate, PageNumberPagination
from ninja.security import django_auth

from discussion.services import DiscussionService

# Initialize Ninja API
router = Router(auth=django_auth)


# Schema definitions
class MessageSchema(Schema):
    id: int
    text: str
    created_at: datetime
    is_current_user: bool
    first_of_group: Optional[bool] = None
    formatted_datetime: Optional[str] = None


class CreateMessageSchema(Schema):
    text: str


class DiscussionListSchema(Schema):
    id: int
    debate_id: int
    debate_title: Optional[str] = None
    participant1_id: int
    participant2_id: int
    latest_message_text: Optional[str] = None
    latest_message_created_at: Optional[datetime] = None
    latest_message_author: Optional[str] = None
    is_unread: bool
    recent_date: datetime


class DiscussionDetailSchema(Schema):
    id: int
    debate_id: int
    debate_title: Optional[str] = None
    participant1_id: int
    participant2_id: int
    is_archived_for_current_user: bool
    created_at: datetime


class DiscussionInfoSchema(Schema):
    id: int
    debate_id: int
    debate_title: str
    participant1_id: int
    participant1_username: str
    participant1_stance: str
    participant2_id: int
    participant2_username: str
    participant2_stance: str
    message_count: int
    is_from_invite: bool
    invite_id: Optional[int] = None
    is_archived_for_current_user: bool


class ArchiveStatusSchema(Schema):
    status: bool


class CreateDiscussionSchema(Schema):
    debate_id: int
    participant2_id: int


class ReadCheckpointSchema(Schema):
    user_id: int
    last_message_read_id: Optional[int] = None
    read_at: Optional[datetime] = None


# API Endpoints
@router.get("/", response=List[DiscussionListSchema])
@paginate(PageNumberPagination, page_size=15)
def get_discussions(request, filterType: Optional[Literal["active", "archived"]] = None):
    """
    Get the most recent discussions for the current user.
    """
    return DiscussionService.get_discussions_for_user(request.user, filterType)


@router.get("/most-recent", response=DiscussionDetailSchema)
def get_most_recent_discussion(request):
    """
    Get the most recent active discussion for the current user.
    """
    discussion = DiscussionService.get_discussions_for_user(request.user, 'active').first()
    if not discussion:
        return router.create_response(request, {"detail": "No active discussions found"}, status=404)

    # Add is_archived_for_current_user
    discussion.is_archived_for_current_user = discussion.is_archived_for(request.user)
    return discussion


@router.get("/{discussion_id}", response=DiscussionDetailSchema)
def get_discussion(request, discussion_id: int):
    """
    Get a specific discussion.
    """
    return DiscussionService.get_discussion_detail(discussion_id, request.user)


@router.get("/{discussion_id}/messages", response=List[MessageSchema])
@paginate(PageNumberPagination, page_size=30)
def get_discussion_messages(request, discussion_id: int):
    """
    Get messages for a specific discussion.
    """
    return DiscussionService.get_discussion_messages(discussion_id, request.user)


@router.get("/{discussion_id}/info", response=DiscussionInfoSchema)
def get_discussion_info(request, discussion_id: int):
    """
    Get detailed information about a discussion.
    """
    return DiscussionService.get_discussion_info(discussion_id, request.user)


@router.patch("/{discussion_id}/archive", response=DiscussionDetailSchema)
def set_archive_status(request, discussion_id: int, payload: ArchiveStatusSchema):
    """
    Archive or unarchive a discussion.
    """
    return DiscussionService.set_discussion_archive_status(discussion_id, request.user, payload.status)


@router.get("/{discussion_id}/readcheckpoints", response=List[ReadCheckpointSchema])
def get_read_checkpoints(request, discussion_id: int):
    """
    Get the read checkpoints for a discussion.
    """
    return DiscussionService.get_read_checkpoints(discussion_id, request.user)
