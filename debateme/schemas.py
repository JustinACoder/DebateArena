from datetime import datetime

from ninja import Schema
from ninja.orm import create_schema

from debate.schemas import DebateSchema
from debateme.models import InviteUse
from users.schemas import UserSchema


class InviteSchema(Schema):
    id: int
    code: str
    debate: DebateSchema
    creator: UserSchema
    created_at: datetime

InviteUseSchema = create_schema(
    InviteUse,
    depth=0
)
