from django.urls import path
from .views import (
    ProductListView, ProductCreateView, ProductDetailView, ProductVariantCreateView,
    CertificadoAprovacaoListView, CertificadoAprovacaoCreateView, PPEDeliveryListView,
    PPEDeliveryCreateView, delivery_sign_view
)

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('add/', ProductCreateView.as_view(), name='product_create'),
    path('<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
    path('<int:product_pk>/variants/add/', ProductVariantCreateView.as_view(), name='variant_create'),
    
    path('ca/', CertificadoAprovacaoListView.as_view(), name='ca_list'),
    path('ca/add/', CertificadoAprovacaoCreateView.as_view(), name='ca_create'),
    
    path('deliveries/', PPEDeliveryListView.as_view(), name='delivery_list'),
    path('deliveries/add/', PPEDeliveryCreateView.as_view(), name='delivery_create'),
    path('deliveries/<int:pk>/sign/', delivery_sign_view, name='delivery_sign'),
]
