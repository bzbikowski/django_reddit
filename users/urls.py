from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.register, name="register"),
    path('login/', views.user_login, name="login"),
    path('logout/', views.user_logout, name="logout"),
    path('user/<str:username>', views.user_profile, name="user_profile"),
    path('profile/edit/', views.edit_profile, name="edit_profile"),
]
