from rest_framework import serializers
from .models import Submission, Comment
from rest_framework_recursive.fields import RecursiveField


class CommentSerializer(serializers.ModelSerializer):
    children = serializers.ListSerializer(child=RecursiveField())

    class Meta:
        model = Comment
        fields = '__all__'


class SubmissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Submission
        exclude = ['author',]



