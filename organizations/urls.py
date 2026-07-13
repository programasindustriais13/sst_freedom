from django.urls import path
from .views import (
    OrganizationDashboardView, CompanyCreateView, UnitCreateView,
    SectorCreateView, CostCenterCreateView, FunctionCreateView,
    InventoryLocationCreateView, FunctionDetailView
)

urlpatterns = [
    path('', OrganizationDashboardView.as_view(), name='organization_dashboard'),
    path('company/add/', CompanyCreateView.as_view(), name='company_create'),
    path('unit/add/', UnitCreateView.as_view(), name='unit_create'),
    path('sector/add/', SectorCreateView.as_view(), name='sector_create'),
    path('cost-center/add/', CostCenterCreateView.as_view(), name='cost_center_create'),
    path('function/add/', FunctionCreateView.as_view(), name='function_create'),
    path('function/<int:pk>/', FunctionDetailView.as_view(), name='function_detail'),
    path('location/add/', InventoryLocationCreateView.as_view(), name='location_create'),
]

