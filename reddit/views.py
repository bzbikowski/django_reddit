from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponseBadRequest, Http404, \
    HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from reddit.forms import SubmissionForm, SubredditForm
from reddit.models import Submission, Comment, Vote, Subreddit
from users.models import RedditUser, Subscriber
from reddit.serializers import CommentSerializer, SubmissionSerializer
from django.views.decorators.http import require_http_methods
from django.utils import timezone


def frontpage(request):
    all_subreddits = Subreddit.objects.all()
    paginator = Paginator(all_subreddits, 20)

    page = request.GET.get('page', 1)
    try:
        subreddits = paginator.page(page)
    except PageNotAnInteger:
        raise Http404
    except EmptyPage:
        subreddits = paginator.page(paginator.num_pages)
    if request.user.is_authenticated:
        reddit_user = RedditUser.objects.get(user=request.user)
        subscribed_subs = Subscriber.objects.filter(user=reddit_user)
        list_of_subreddits = [sub.subscribed_to for sub in subscribed_subs]
        return render(request, 'public/frontpage.html', {'subreddits': subreddits, 'subscribed_to': list_of_subreddits})
    return render(request, 'public/frontpage.html', {'subreddits': subreddits})


def subreddit(request, sub=None, format=None):
    this_subreddit = get_object_or_404(Subreddit, name_id=sub)
    all_posts = Submission.objects.filter(subreddit=this_subreddit)
    paginator = Paginator(all_posts, 20)

    page = request.GET.get('page', 1)
    try:
        submissions = paginator.page(page)
    except PageNotAnInteger:
        raise Http404
    except EmptyPage:
        submissions = paginator.page(paginator.num_pages)

    submission_votes = {}

    if request.user.is_authenticated:
        for submission in submissions:
            try:
                vote = Vote.objects.get(
                    vote_object_type=submission.get_content_type(),
                    vote_object_id=submission.id,
                    user=RedditUser.objects.get(user=request.user))
                submission_votes[submission.id] = vote.value
            except Vote.DoesNotExist:
                pass

    return render(request, 'public/subreddit.html', {'subreddit': this_subreddit,
                                                     'submissions': submissions,
                                                     'submission_votes': submission_votes})


def comments(request, sub=None, thread_id=None, format=None):
    """
    Handles comment view when user opens the thread.
    On top of serving all comments in the thread it will
    also return all votes user made in that thread
    so that we can easily update comments in template
    and display via css whether user voted or not.

    :param thread_id: Thread ID as it's stored in database
    :type thread_id: int
    """
    this_subreddit = get_object_or_404(Subreddit, name_id=sub)

    this_submission = get_object_or_404(Submission, subreddit=this_subreddit, id=thread_id)

    thread_comments = Comment.objects.filter(submission=this_submission)

    if request.user.is_authenticated:
        try:
            reddit_user = RedditUser.objects.get(user=request.user)
        except RedditUser.DoesNotExist:
            reddit_user = None
    else:
        reddit_user = None

    sub_vote_value = None
    comment_votes = {}

    if reddit_user:

        try:
            vote = Vote.objects.get(
                vote_object_type=this_submission.get_content_type(),
                vote_object_id=this_submission.id,
                user=reddit_user)
            sub_vote_value = vote.value
        except Vote.DoesNotExist:
            pass

        try:
            user_thread_votes = Vote.objects.filter(user=reddit_user,
                                                    submission=this_submission)

            for vote in user_thread_votes:
                comment_votes[vote.vote_object.id] = vote.value
        except:
            pass
    if format == 'json':
        thread_comments = Comment.objects.filter(submission=this_submission, parent=None)
        s_serializer = SubmissionSerializer(this_submission, many=False)
        c_serializer = CommentSerializer(thread_comments, many=True)
        return JsonResponse([s_serializer.data, c_serializer.data], safe=False)
    else:
        return render(request, 'public/comments.html',
                      {'submission': this_submission,
                       'comments': thread_comments,
                       'comment_votes': comment_votes,
                       'sub_vote': sub_vote_value})


@require_http_methods(["POST"])
def post_comment(request):
    if not request.user.is_authenticated:
        return JsonResponse({'msg': "You need to log in to post new comments."})

    parent_type = request.POST.get('parentType', None)
    parent_id = request.POST.get('parentId', None)
    raw_comment = request.POST.get('commentContent', None)

    if not all([parent_id, parent_type]) or \
            parent_type not in ['comment', 'submission'] or \
        not parent_id.isdigit():
        return HttpResponseBadRequest()

    if not raw_comment:
        return JsonResponse({'msg': "You have to write something."})
    author = RedditUser.objects.get(user=request.user)
    parent_object = None
    try:  # try and get comment or submission we're voting on
        if parent_type == 'comment':
            parent_object = Comment.objects.get(id=parent_id)
        elif parent_type == 'submission':
            parent_object = Submission.objects.get(id=parent_id)

    except (Comment.DoesNotExist, Submission.DoesNotExist):
        return HttpResponseBadRequest()

    comment = Comment.create(author=author,
                             raw_comment=raw_comment,
                             parent=parent_object)

    comment.save()
    return JsonResponse({'msg': "Your comment has been posted."})


@require_http_methods(["POST"])
def post_subscribe(request, sub):
    if not request.user.is_authenticated:
        messages.error(request, "You need to log in to subscribe new subreddits.")
        return redirect(request.META['HTTP_REFERER'])
    user = RedditUser.objects.get(user=request.user)
    subreddit = Subreddit.objects.get(name_id=sub)
    subscriber = Subscriber(user=user, subscribed_to=subreddit)
    subscriber.save()
    subreddit.subscribe()
    subreddit.save()
    messages.success(request, "Successful subscription.")
    return redirect(request.META['HTTP_REFERER'])


@require_http_methods(["POST"])
def post_unsubscribe(request, sub):
    user = RedditUser.objects.get(user=request.user)
    subreddit = Subreddit.objects.get(name_id=sub)
    subscriber = Subscriber.objects.get(user=user, subscribed_to=subreddit)
    subscriber.delete()
    subreddit.unsubscribe()
    subreddit.save()
    messages.success(request, "Successful unsubscription.")
    return redirect(request.META['HTTP_REFERER'])


def vote(request):
    # The type of object we're voting on, can be 'submission' or 'comment'
    vote_object_type = request.POST.get('what', None)

    # The ID of that object as it's stored in the database, positive int
    vote_object_id = request.POST.get('what_id', None)

    # The value of the vote we're writing to that object, -1 or 1
    # Passing the same value twice will cancel the vote i.e. set it to 0
    new_vote_value = request.POST.get('vote_value', None)

    # By how much we'll change the score, used to modify score on the fly
    # client side by the javascript instead of waiting for a refresh.
    vote_diff = 0

    if not request.user.is_authenticated:
        return HttpResponseForbidden()
    else:
        user = RedditUser.objects.get(user=request.user)

    try:  # If the vote value isn't an integer that's equal to -1 or 1
        # the request is bad and we can not continue.
        new_vote_value = int(new_vote_value)

        if new_vote_value not in [-1, 1]:
            raise ValueError("Wrong value for the vote!")

    except (ValueError, TypeError):
        return HttpResponseBadRequest()

    # if one of the objects is None, 0 or some other bool(value) == False value
    # or if the object type isn't 'comment' or 'submission' it's a bad request
    if not all([vote_object_type, vote_object_id, new_vote_value]) or \
            vote_object_type not in ['comment', 'submission']:
        return HttpResponseBadRequest()

    # Try and get the actual object we're voting on.
    try:
        if vote_object_type == "comment":
            vote_object = Comment.objects.get(id=vote_object_id)

        elif vote_object_type == "submission":
            vote_object = Submission.objects.get(id=vote_object_id)
        else:
            return HttpResponseBadRequest()  # should never happen

    except (Comment.DoesNotExist, Submission.DoesNotExist):
        return HttpResponseBadRequest()

    # Try and get the existing vote for this object, if it exists.
    try:
        vote = Vote.objects.get(vote_object_type=vote_object.get_content_type(),
                                vote_object_id=vote_object.id,
                                user=user)

    except Vote.DoesNotExist:
        # Create a new vote and that's it.
        vote = Vote.create(user=user,
                           vote_object=vote_object,
                           vote_value=new_vote_value)
        vote.save()
        vote_diff = new_vote_value
        return JsonResponse({'error'   : None,
                             'voteDiff': vote_diff})

    # User already voted on this item, this means the vote is either
    # being canceled (same value) or changed (different new_vote_value)
    if vote.value == new_vote_value:
        # canceling vote
        vote_diff = vote.cancel_vote()
        if not vote_diff:
            return HttpResponseBadRequest(
                'Something went wrong while canceling the vote')
    else:
        # changing vote
        vote_diff = vote.change_vote(new_vote_value)
        if not vote_diff:
            return HttpResponseBadRequest(
                'Wrong values for old/new vote combination')

    return JsonResponse({'error'   : None,
                         'voteDiff': vote_diff})


@login_required
def submit(request, sub=None):
    """
    Handles new submission.. submission.
    """
    submission_form = SubmissionForm()

    if request.method == 'POST':
        submission_form = SubmissionForm(request.POST)
        if submission_form.is_valid():
            submission = submission_form.save(commit=False)
            submission.generate_html()
            user = User.objects.get(username=request.user)
            redditUser = RedditUser.objects.get(user=user)
            submission.author = redditUser
            submission.author_name = user.username
            submission.subreddit = Subreddit.objects.get(name_id=sub)
            submission.save()
            messages.success(request, 'Submission created')
            return redirect('/r/{}/{}'.format(sub, submission.id))

    return render(request, 'public/submit.html', {'form': submission_form, 'sub': sub})


@login_required
def create_subreddit(request):
    reddit_user = RedditUser.objects.get(user=request.user)
    if reddit_user.check_creating_prev():
        messages.info(request, 'You need to have at least 30 days old account to make a subreddit.')
        return redirect(request.META['HTTP_REFERER'])

    subreddit_form = SubredditForm()

    if request.method == 'POST':
        subreddit_form = SubredditForm(request.POST)
        if subreddit_form.is_valid():
            subreddit = subreddit_form.save(commit=False)
            user = User.objects.get(username=request.user)
            redditUser = RedditUser.objects.get(user=user)
            subreddit.admin = redditUser
            subreddit.admin_name = user.username
            subreddit.generate_link()
            subreddit.save()
            messages.success(request, 'Subreddit created')
            return redirect(subreddit.http_link)

    return render(request, 'public/create_subreddit.html', {'form': subreddit_form})
