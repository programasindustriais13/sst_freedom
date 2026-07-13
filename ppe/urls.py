from django.urls import path
from .views import (
    ProductListView, ProductCreateView, ProductUpdateView, ProductDetailView, ProductVariantCreateView,
    CertificadoAprovacaoListView, CertificadoAprovacaoCreateView, PPEDeliveryListView,
    PPEDeliveryCreateView, delivery_sign_view, product_search_ajax, product_add_ajax,
    PPEMatrixCreateView, PPEMatrixUpdateView, ppe_matrix_toggle_active,
    PPEMatrixListView, PPEMatrixBulkCreateView, PPEMatrixBulkUpdateView, PPEMatrixBulkDeleteView
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
    
    path('matrix/add/<int:function_pk>/', PPEMatrixCreateView.as_view(), name='ppe_matrix_create'),
    path('matrix/<int:pk>/edit/', PPEMatrixUpdateView.as_view(), name='ppe_matrix_update'),
    path('matrix/<int:pk>/toggle/', ppe_matrix_toggle_active, name='ppe_matrix_toggle_active'),
    
    # Novas rotas da interface própria/bulk
    path('matrices/', PPEMatrixListView.as_view(), name='matrix_list'),
    path('matrices/add/', PPEMatrixBulkCreateView.as_view(), name='matrix_bulk_create'),
    path('matrices/function/<int:function_pk>/edit/', PPEMatrixBulkUpdateView.as_view(), name='matrix_bulk_update'),
    path('matrices/function/<int:function_pk>/delete/', PPEMatrixBulkDeleteView.as_view(), name='matrix_bulk_delete'),
]


