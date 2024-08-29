from django import forms
from .models import Message


class MessageForm(forms.ModelForm):
    text = forms.CharField(required=True, max_length=5000, strip=True)

    class Meta:
        model = Message
        fields = ['text']
