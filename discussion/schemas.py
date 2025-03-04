# Schema definitions
from datetime import datetime
from typing import Optional

from ninja import Schema


class MessageSchema(Schema):
    id: int
    text: str
    created_at: datetime
    is_current_user: bool


class CreateMessageSchema(Schema):
    text: str


class DiscussionListSchema(Schema):
    id: int
    debate_id: int
    debate_title: str = None
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