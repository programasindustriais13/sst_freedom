from django.urls import path
from .views import EmployeeListView, EmployeeCreateView, EmployeeDetailView, EmployeeUpdateView, employee_search_ajax

urlpatterns = [
    path('', EmployeeListView.as_view(), name='employee_list'),
    path('add/', EmployeeCreateView.as_view(), name='employee_create'),
    path('<int:pk>/', EmployeeDetailView.as_view(), name='employee_detail'),
    path('<int:pk>/edit/', EmployeeUpdateView.as_view(), name='employee_update'),
    path('api/search/', employee_search_ajax, name='employee_api_search'),
    path('search_ajax/', employee_search_ajax, name='employee_search_ajax'),
]

