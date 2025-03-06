from ninja import ModelSchema

from debate.models import Debate, Comment, Stance
from users.schemas import UserSchema


class DebateSchema(ModelSchema):
    author: UserSchema

    class Config:
        model = Debate
        model_exclude = ['search_vector']


class CommentSchema(ModelSchema):
    author: UserSchema

    class Config:
        model = Comment
        model_fields = '__all__'
        model_depth = 0

class StanceSchema(ModelSchema):
    user: UserSchema
    class Config:
        model = Stance
        model_fields = '__all__'
        model_depth = 0
