from django import forms
from .models import Message


class MessageForm(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea(attrs={
        'rows': 1,
        'id': 'message-text-input',
        'style': 'resize: none; overflow: hidden;',
        'placeholder': 'Type your message here...'
    }), label='', required=True, max_length=5000, strip=True)

    class Meta:
        model = Message
        fields = ['text']
