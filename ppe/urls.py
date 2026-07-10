from django.urls import path
from .views import (
    ProductListView, ProductCreateView, ProductUpdateView, ProductDetailView, ProductVariantCreateView,
    CertificadoAprovacaoListView, CertificadoAprovacaoCreateView, PPEDeliveryListView,
    PPEDeliveryCreateView, delivery_sign_view, product_search_ajax, product_add_ajax
)

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('add/', ProductCreateView.as_view(), name='product_create'),
    path('<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
    path('<int:pk>/edit/', ProductUpdateView.as_view(), name='product_update'),
    path('<int:product_pk>/variants/add/', ProductVariantCreateView.as_view(), name='variant_create'),
    
    path('ca/', CertificadoAprovacaoListView.as_view(), name='ca_list'),
    path('ca/add/', CertificadoAprovacaoCreateView.as_view(), name='ca_create'),
    
    path('deliveries/', PPEDeliveryListView.as_view(), name='delivery_list'),
    path('deliveries/add/', PPEDeliveryCreateView.as_view(), name='delivery_create'),
    path('deliveries/<int:pk>/sign/', delivery_sign_view, name='delivery_sign'),
    
    path('add/ajax/', product_add_ajax, name='product_add_ajax'),
    path('search_ajax/', product_search_ajax, name='product_search_ajax'),
]
