from ninja import ModelSchema

from debate.models import Debate


class DebateSchema(ModelSchema):
    class Meta:
        model = Debate
        exclude = ['search_vector']