from django.urls import path
from .views import AlertListView, resolve_alert_view

urlpatterns = [
    path('', AlertListView.as_view(), name='alert_list'),
    path('<int:pk>/resolve/', resolve_alert_view, name='alert_resolve'),
]
