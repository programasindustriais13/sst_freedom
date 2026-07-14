"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from core.views import (
    DashboardView, ReportListView, ReportStockPositionView,
    ReportStockMovementsView, ReportPPEDeliveriesView, ReportCAValidityView
)

def service_worker(request):
    return HttpResponse(
        "// Service Worker placeholder\n",
        content_type="application/javascript"
    )

urlpatterns = [
    path("service-worker.js", service_worker, name="service_worker"),
    path("admin/", admin.site.urls),
    path("", DashboardView.as_view(), name="dashboard"),
    
    # Relatórios
    path("reports/", ReportListView.as_view(), name="report_list"),
    path("reports/stock-position/", ReportStockPositionView.as_view(), name="report_stock_position"),
    path("reports/stock-movements/", ReportStockMovementsView.as_view(), name="report_stock_movements"),
    path("reports/ppe-deliveries/", ReportPPEDeliveriesView.as_view(), name="report_ppe_deliveries"),
    path("reports/ca-validity/", ReportCAValidityView.as_view(), name="report_ca_validity"),
    
    # Módulos
    path("accounts/", include("accounts.urls")),
    path("organizations/", include("organizations.urls")),
    path("employees/", include("employees.urls")),
    path("inventory/", include("inventory.urls")),
    path("ppe/", include("ppe.urls")),
    path("notifications/", include("notifications.urls")),
]

