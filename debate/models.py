from django.db import models


class Debate(models.Model):
    title = models.CharField(max_length=100, primary_key=True)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    author = models.CharField(max_length=100)

    def __str__(self):
        return f"\"{self.title}\" by {self.author}"


class Argument(models.Model):
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    content = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    author = models.CharField(max_length=100)

    def __str__(self):
        return f"\"{self.title}\" by {self.author}"
