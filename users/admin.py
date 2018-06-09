from django.contrib import admin

# Register your models here.
from reddit.admin import SubmissionInline
from users.models import RedditUser, Subscriber


class SubscriptionInline(admin.TabularInline):
    model = Subscriber
    max_num = 5


class RedditUserAdmin(admin.ModelAdmin):
    inlines = [
        SubmissionInline,
        SubscriptionInline,
    ]


admin.site.register(RedditUser, RedditUserAdmin)
admin.site.register(Subscriber)
