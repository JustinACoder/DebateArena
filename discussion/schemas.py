# Schema definitions
from datetime import datetime
from typing import Optional

from ninja import Schema, ModelSchema

from debate.schemas import DebateSchema
from discussion.models import ReadCheckpoint, Message, Discussion
from debateme.schemas import InviteSchema
from users.schemas import UserSchema


class MessageSchema(ModelSchema):
    # is_current_user: bool # do we need this?
    class Config:
        model = Message
        model_fields = '__all__'
        model_depth = 0


class DiscussionSchema(ModelSchema):
    debate: DebateSchema
    participant1: UserSchema
    participant2: UserSchema
    latest_message_text: Optional[str]
    latest_message_created_at: Optional[datetime]
    latest_message_author: Optional[str]
    is_archived_for_current_user: bool
    is_unread: bool
    recent_date: datetime
    is_from_invite: bool
    invite_id: Optional[int]

    class Config:
        model = Discussion
        model_fields = '__all__'


class ReadCheckpointSchema(ModelSchema):
    class Config:
        model = ReadCheckpoint
        model_fields = '__all__'
        model_depth = 0
