from django.contrib import admin
from reddit.models import Submission,Comment,Vote,Subreddit


# Register your models here.
class SubmissionInline(admin.TabularInline):
    model = Submission
    max_num = 10


class CommentsInline(admin.StackedInline):
    model = Comment
    max_num = 10


class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'author')
    inlines = [CommentsInline]


class SubredditAdmin(admin.ModelAdmin):
    list_display = ('title', 'sub_count', 'http_link')
    search_fields = ['title']


admin.site.register(Subreddit, SubredditAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(Comment)
admin.site.register(Vote)
