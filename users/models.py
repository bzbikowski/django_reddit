from hashlib import md5

import mistune
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models


class RedditUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.DO_NOTHING)
    first_name = models.CharField(max_length=35, null=True, default=None,
                                  blank=True)
    last_name = models.CharField(max_length=35, null=True, default=None,
                                 blank=True)
    email = models.EmailField(null=True, blank=True, default=None)
    about_text = models.TextField(blank=True, null=True, max_length=500,
                                  default=None)
    about_html = models.TextField(blank=True, null=True, default=None)
    gravatar_hash = models.CharField(max_length=32, null=True, blank=True,
                                     default=None)
    display_picture = models.NullBooleanField(default=False)
    homepage = models.URLField(null=True, blank=True, default=None)
    twitter = models.CharField(null=True, blank=True, max_length=15,
                               default=None)
    github = models.CharField(null=True, blank=True, max_length=39,
                              default=None)

    comment_karma = models.IntegerField(default=0)
    link_karma = models.IntegerField(default=0)

    def update_profile_data(self):
        self.about_html = mistune.markdown(self.about_text)
        if self.display_picture:
            self.gravatar_hash = md5(self.email.lower().encode('utf-8')).hexdigest()

    def check_creating_prev(self):
        return (timezone.now() - self.user.date_joined).total_seconds() < 30*24*60*60

    def __str__(self):
        return "<RedditUser:{}>".format(self.user.username)


class Subscriber(models.Model):
    user = models.ForeignKey(RedditUser, on_delete=models.CASCADE)
    subscribed_to = models.ForeignKey('reddit.Subreddit', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"<Subscriber:{self.user.user.username}->{self.subscribed_to.title}"
