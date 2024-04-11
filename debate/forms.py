from django.forms import ModelForm
from .models import Debate, Argument


class DebateForm(ModelForm):
    class Meta:
        model = Debate
        fields = ['title', 'description', 'author']


class ArgumentForm(ModelForm):
    class Meta:
        model = Argument
        fields = ['title', 'content', 'author']
