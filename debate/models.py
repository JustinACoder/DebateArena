from django.conf import settings
from django.db import models
from django.template.defaultfilters import slugify


class Debate(models.Model):
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    slug = models.SlugField(max_length=100, unique=True)  # WARNING: not generated automatically if using bulk_create

    def save(self, *args, **kwargs):
        # If the debate is new, generate a slug
        if not self.id:
            self.slug = slugify(self.title)

            # get the count of debates with the same slug
            count = Debate.objects.filter(slug=self.slug).count()

            # If there are debates with the same slug, append a number to the slug
            if count > 0:
                self.slug = f"{self.slug}-{count}"

        super(Debate, self).save(*args, **kwargs)

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


class Stance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE)
    stance = models.BooleanField()  # False for "against", True for "for" # TODO: think of a more complex stance system

    class Meta:
        unique_together = ('user', 'debate')  # A user can only have one stance on a debate

    def __str__(self):
        return f"Stance of {self.user} on \"{self.debate.title}\""
