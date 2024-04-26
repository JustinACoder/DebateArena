from django.forms import ModelForm
from .models import Debate, Comment


class DebateForm(ModelForm):
    class Meta:
        model = Debate
        fields = ['title', 'description']

class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
