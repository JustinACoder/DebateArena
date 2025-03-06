from ninja import Schema, ModelSchema

from debate.schemas import DebateSchema
from debateme.models import InviteUse, Invite
from users.schemas import UserSchema


class InviteSchema(ModelSchema):
    debate: DebateSchema
    creator: UserSchema

    class Config:
        model = Invite
        model_fields = '__all__'

class InviteUseSchema(ModelSchema):
    user: UserSchema

    class Config:
        model = InviteUse
        model_fields = '__all__'
        model_depth = 0
