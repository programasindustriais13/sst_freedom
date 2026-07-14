from django.contrib.auth.views import LoginView
from django.urls import path
from .views import SafeLogoutView

urlpatterns = [
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', SafeLogoutView.as_view(next_page='login'), name='logout'),
]

