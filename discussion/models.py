from django.conf import settings
from django.db import models
from debate.models import Debate


class Discussion(models.Model):
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE)
    participant1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='participant1')
    participant2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='participant2')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def participants(self):
        return [self.participant1, self.participant2]

    def __str__(self):
        return f"Discussion between {self.participant1} and {self.participant2} on \"{self.debate.title}\""


class Message(models.Model):
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message {self.id} by {self.author} in discussion on \"{self.discussion.debate.title}\""

