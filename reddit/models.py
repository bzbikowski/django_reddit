import mistune
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from users.models import RedditUser
from django.db import models
from django.utils import timezone
from mptt.models import MPTTModel, TreeForeignKey


class Subreddit(models.Model):
    admin = models.ForeignKey(RedditUser, on_delete=models.DO_NOTHING)
    admin_name = models.CharField(null=False, max_length=12)
    title = models.CharField(max_length=60)
    description = models.TextField(max_length=1000)
    timestamp = models.DateTimeField(default=timezone.now)
    name_id = models.CharField(primary_key=True, max_length=30)
    http_link = models.TextField()
    sub_count = models.PositiveIntegerField(default=0)

    def generate_link(self):
        self.http_link = f"/r/{self.name_id}"

    def __str__(self):
        return f"<Subreddit: {self.title}>"

    def subscribe(self):
        self.sub_count += 1

    def unsubscribe(self):
        self.sub_count -= 1


class Submission(models.Model):
    author_name = models.CharField(null=False, max_length=12)
    author = models.ForeignKey('users.RedditUser', on_delete=models.CASCADE)
    title = models.CharField(max_length=250)
    url = models.URLField(null=True, blank=True)
    text = models.TextField(max_length=5000, blank=True)
    text_html = models.TextField(blank=True)
    ups = models.IntegerField(default=0)
    downs = models.IntegerField(default=0)
    score = models.IntegerField(default=0)
    timestamp = models.DateTimeField(default=timezone.now)
    comment_count = models.IntegerField(default=0)
    subreddit = models.ForeignKey(Subreddit, on_delete=models.CASCADE)

    def generate_html(self):
        if self.text:
            html = mistune.markdown(self.text)
            self.text_html = html

    @property
    def linked_url(self):
        if self.url:
            return "{}".format(self.url)
        else:
            return "/r/{}/{}".format(self.subreddit.name_id, self.id)

    @property
    def comments_url(self):
        return "/r/{}/{}".format(self.subreddit.name_id, self.id)

    def __str__(self):
        return "<Submission:{}>".format(self.id)

    def get_content_type(self):
        """:return: Content type for this instance."""
        return ContentType.objects.get_for_model(self)

    def get_content_type_id(self):
        """:return: Content type ID for this instance"""
        return self.get_content_type().pk

    def add_vote(self, vote_value):
        self.score += vote_value
        if vote_value == 1:
            self.ups += 1
        elif vote_value == -1:
            self.downs += 1


class Comment(MPTTModel):
    author_name = models.CharField(null=False, max_length=12)
    author = models.ForeignKey('users.RedditUser', on_delete=models.CASCADE)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    parent = TreeForeignKey('self', related_name='children',
                            null=True, blank=True, db_index=True, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    ups = models.IntegerField(default=0)
    downs = models.IntegerField(default=0)
    score = models.IntegerField(default=0)
    raw_comment = models.TextField(blank=True)
    html_comment = models.TextField(blank=True)

    class MPTTMeta:
        order_insertion_by = ['-score']

    @classmethod
    def create(cls, author, raw_comment, parent):
        """
        Create a new comment instance. If the parent is submisison
        update comment_count field and save it.
        If parent is comment post it as child comment
        :param author: RedditUser instance
        :type author: RedditUser
        :param raw_comment: Raw comment text
        :type raw_comment: str
        :param parent: Comment or Submission that this comment is child of
        :type parent: Comment | Submission
        :return: New Comment instance
        :rtype: Comment
        """

        html_comment = mistune.markdown(raw_comment)
        # todo: any exceptions possible?
        comment = cls(author=author,
                      author_name=author.user.username,
                      raw_comment=raw_comment,
                      html_comment=html_comment)

        if isinstance(parent, Submission):
            submission = parent
            comment.submission = submission
        elif isinstance(parent, Comment):
            submission = parent.submission
            comment.submission = submission
            comment.parent = parent
        else:
            return
        submission.comment_count += 1
        submission.save()

        return comment

    def __str__(self):
        return "<Comment:{}>".format(self.id)

    def get_content_type(self):
        """:return: Content type for this instance."""
        return ContentType.objects.get_for_model(self)

    def get_content_type_id(self):
        """:return: Content type ID for this instance"""
        return self.get_content_type().pk


class Vote(models.Model):
    user = models.ForeignKey('users.RedditUser', on_delete=models.CASCADE)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    vote_object_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    vote_object_id = models.PositiveIntegerField()
    vote_object = GenericForeignKey('vote_object_type', 'vote_object_id')
    value = models.IntegerField(default=0)

    @classmethod
    def create(cls, user, vote_object, vote_value):
        """
        Create a new vote object and return it.
        It will also update the ups/downs/score fields in the
        vote_object instance and save it.

        :param user: RedditUser instance
        :type user: RedditUser
        :param vote_object: Instance of the object the vote is cast on
        :type vote_object: Comment | Submission
        :param vote_value: Value of the vote
        :type vote_value: int
        :return: new Vote instance
        :rtype: Vote
        """

        if isinstance(vote_object, Submission):
            submission = vote_object
            vote_object.author.link_karma += vote_value
        else:
            submission = vote_object.submission
            vote_object.author.comment_karma += vote_value

        vote = cls(user=user,
                   vote_object=vote_object,
                   value=vote_value)

        vote.submission = submission
        # the value for new vote will never be 0
        # that can happen only when removing up/down vote.
        vote_object.score += vote_value
        if vote_value == 1:
            vote_object.ups += 1
        elif vote_value == -1:
            vote_object.downs += 1

        vote_object.save()
        vote_object.author.save()

        return vote

    def change_vote(self, new_vote_value):
        if self.value == -1 and new_vote_value == 1:  # down to up
            vote_diff = 2
            self.vote_object.score += 2
            self.vote_object.ups += 1
            self.vote_object.downs -= 1
        elif self.value == 1 and new_vote_value == -1:  # up to down
            vote_diff = -2
            self.vote_object.score -= 2
            self.vote_object.ups -= 1
            self.vote_object.downs += 1
        elif self.value == 0 and new_vote_value == 1:  # canceled vote to up
            vote_diff = 1
            self.vote_object.ups += 1
            self.vote_object.score += 1
        elif self.value == 0 and new_vote_value == -1:  # canceled vote to down
            vote_diff = -1
            self.vote_object.downs += 1
            self.vote_object.score -= 1
        else:
            return None

        if isinstance(self.vote_object, Submission):
            self.vote_object.author.link_karma += vote_diff
        else:
            self.vote_object.author.comment_karma += vote_diff

        self.value = new_vote_value
        self.vote_object.save()
        self.vote_object.author.save()
        self.save()

        return vote_diff

    def cancel_vote(self):
        if self.value == 1:
            vote_diff = -1
            self.vote_object.ups -= 1
            self.vote_object.score -= 1
        elif self.value == -1:
            vote_diff = 1
            self.vote_object.downs -= 1
            self.vote_object.score += 1
        else:
            return None

        if isinstance(self.vote_object, Submission):
            self.vote_object.author.link_karma += vote_diff
        else:
            self.vote_object.author.comment_karma += vote_diff

        self.value = 0
        self.save()
        self.vote_object.save()
        self.vote_object.author.save()
        return vote_diff
