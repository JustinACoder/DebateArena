from django.conf import settings
from django.db import models


class Debate(models.Model):
    title = models.CharField(max_length=100, primary_key=True)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"\"{self.title}\" by {self.author}"


class Comment(models.Model):
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    date_added = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.author} on \"{self.debate.title}\""
