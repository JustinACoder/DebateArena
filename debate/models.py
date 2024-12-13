from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Count, Case, When, Window, Max, Q
from django.template.defaultfilters import slugify
from django.db.models import F, Func, Value, StdDev
from django.db.models.functions import Coalesce, Log, Greatest, Now, Abs, Cast
from voting.models import Vote
from datetime import timedelta


class DebateManager(models.Manager):
    def get_popular(self):
        return self.annotate(num_votes=Count('vote')).order_by('-num_votes')

    def get_recent(self):
        return self.order_by('-date')

    def get_trending(self):
        """
        We will keep it simple for now and order by the ratio of votes between now and the maximum between -48 hours
        and the debate's creation date. Then, we multiply by the log2 of the number of votes to give more weight to debates
        with more votes.
        """
        # Get the maximum between -48 hours and the debate's creation date
        past_date = Greatest(F('date'), Now() - timedelta(hours=48))

        # Get the number of votes between the past date and now
        num_votes_since = Count('vote', filter=Q(vote__time_stamp__gte=past_date))

        # Number of votes in total/
        num_votes_total = Count('vote')

        # Calculate the percentage of votes in the period (+1 to avoid division by zero)
        percentage_votes_in_period = num_votes_since / (num_votes_total + 1)

        # Multiply by the log2 of the number of votes (+1 to avoid log(0))
        score = percentage_votes_in_period * Log(2, num_votes_total + 1)

        return self.annotate(num_votes=num_votes_total).annotate(score=score).order_by('-score')

    def get_controversial(self):
        """
        To determine the controversy of a debate, we will calculate the standard deviation of the stances.
        The lower the standard deviation, the more controversial the debate is since it means that the stances are
        more evenly distributed.
        """
        stddev = StdDev(Cast('stance__stance', models.IntegerField()))

        return self.annotate(stance_stddev=stddev).order_by('stance_stddev')

    def get_random(self):
        return self.order_by('?')


class Debate(models.Model):
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    slug = models.SlugField(max_length=100, unique=True)  # WARNING: not generated automatically if using bulk_create
    vote = GenericRelation(Vote, related_query_name='debate')

    objects = DebateManager()

    def get_stance(self, user):
        try:
            return self.stance_set.get(user=user).stance
        except Stance.DoesNotExist:
            return None

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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'debate')  # A user can only have one stance on a debate

    def __str__(self):
        return f"Stance of {self.user} on \"{self.debate.title}\""
