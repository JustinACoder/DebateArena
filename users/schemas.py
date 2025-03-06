from django.contrib.auth import get_user_model
from ninja import ModelSchema

UserModel = get_user_model()

class UserSchema(ModelSchema):
    class Config:
        model = UserModel
        model_exclude = ['password']