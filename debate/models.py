from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.search import SearchVector, SearchVectorField, SearchQuery, SearchRank
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Count, Case, When, Window, Max, Q, OuterRef, Subquery
from django.template.defaultfilters import slugify
from django.db.models import F, Func, Value, StdDev
from django.db.models.functions import Coalesce, Log, Greatest, Now, Abs, Cast
from django.contrib.postgres.indexes import GinIndex
from voting.models import Vote
from datetime import timedelta


class DebateQuerySet(models.QuerySet):
    def with_stance(self, user):
        if user.is_anonymous:
            return self.annotate(user_stance=Value(None, output_field=models.BooleanField()))
        else:
            return self.annotate(
                user_stance=Subquery(
                    Stance.objects.filter(debate=OuterRef('pk'), user=user).values('stance')[:1]
                )
            )


class DebateManager(models.Manager):
    def get_queryset(self):
        return DebateQuerySet(self.model, using=self._db)

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

    def search(self, query: str):
        search_vector = (
                SearchVector('title', weight='A') +
                SearchVector('description', weight='C')
        )
        search_query = SearchQuery(query)

        return self.annotate(
            rank=SearchRank(search_vector, search_query)
        ).filter(rank__gt=0.1).order_by('-rank')


class Debate(models.Model):
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    slug = models.SlugField(max_length=100,
                            unique=True)  # WARNING: not generated automatically if using bulk operations
    vote = GenericRelation(Vote, related_query_name='debate')
    search_vector = SearchVectorField(null=True,
                                      editable=False)  # WARNING: not generated automatically if using bulk operations

    objects = DebateManager()

    class Meta:
        indexes = [
            # Gin index for full-text search
            GinIndex(fields=['search_vector'], name='search_vector_idx')
        ]

    def get_stance(self, user):
        try:
            return self.stance_set.get(user=user).stance
        except Stance.DoesNotExist:
            return None

    def save(self, should_update_search_vector=True, *args, **kwargs):
        is_new = not self.id

        # If the debate is new, generate a slug
        if is_new:
            self.slug = slugify(self.title)

            # get the count of debates with the same slug
            count = Debate.objects.filter(slug=self.slug).count()

            # If there are debates with the same slug, append a number to the slug
            if count > 0:
                self.slug = f"{self.slug}-{count}"

        if not should_update_search_vector:
            super(Debate, self).save(*args, **kwargs)
            return

        # If the want to update the search vector, we need to ensure that we are updating the search vector not inserting
        if should_update_search_vector:
            if is_new:
                super(Debate, self).save(*args, **kwargs)

                # Update the search vector
                # This need to be done in update, not insert, because the search vector is a computed field
                self.search_vector = (
                        SearchVector('title', weight='A') +
                        SearchVector('description', weight='C')
                )

                self.save(should_update_search_vector=False)
            else:
                # If the debate is not new and we want to update the search vector
                self.search_vector = (
                        SearchVector('title', weight='A') +
                        SearchVector('description', weight='C')
                )

                super(Debate, self).save(*args, **kwargs)

    def __str__(self):
        return f"\"{self.title}\" by {self.author}"


class CommentManager(models.Manager):
    def get_debate_comments_page(self, user, debate, page=1, page_size=10):
        """
        Get all comments for a debate ordered by date added
        It also annotates the comments with the user's vote and the number of votes

        :param user: The user instance
        :param debate: The debate instance
        :param page: The page number
        :param page_size: The number of comments per page
        :return: A queryset of comments
        """
        comments = self.filter(debate=debate).order_by('-date_added').select_related('author')

        # Get the page of comments
        paginator = Paginator(comments, page_size)
        comments_page = paginator.get_page(page)

        # Get votes for the comments
        comment_votes = Vote.objects.get_for_user_in_bulk(comments_page, user)

        # Get the number of votes for each comment
        comment_vote_scores = Vote.objects.get_scores_in_bulk(comments)

        # Annotate the comments with the vote information
        for comment in comments:
            key = str(comment.id)
            comment.user_vote = comment_votes.get(key)
            comment.vote_score, comment.num_votes = comment_vote_scores.get(key, {'score': 0, 'num_votes': 0}).values()

        return comments_page


class Comment(models.Model):
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    date_added = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    objects = CommentManager()

    def __str__(self):
        return f"Comment by {self.author} on \"{self.debate.title}\""


class Stance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE)
    stance = models.BooleanField()  # False for "against", True for "for" # TODO: think of a more complex stance system
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'debate')  # A user can only have one stance on a debate
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'debate'])
        ]

    def __str__(self):
        return f"Stance of {self.user} on \"{self.debate.title}\""
