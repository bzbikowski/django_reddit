"""django_reddit URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

urlpatterns = [
    path('', views.frontpage, name='frontpage'),
    path('r/create/', views.create_subreddit, name='create_subreddit'),
    path('r/<str:sub>/', views.subreddit, name='sub'),
    path('r/<str:sub>/<int:thread_id>/', views.comments, name='thread'),
    path('r/<str:sub>/submit/', views.submit, name='submit'),
    path('r/<str:sub>/subscribe/', views.post_subscribe, name='post_subscribe'),
    path('r/<str:sub>/unsubscribe/', views.post_unsubscribe, name='post_unsubscribe'),
    path('post/comment/', views.post_comment, name="post_comment"),
    path('vote/', views.vote, name="vote"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
