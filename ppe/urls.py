from django.urls import path
from .views import (
    ProductListView, ProductCreateView, ProductUpdateView, ProductDetailView, ProductVariantCreateView,
    CertificadoAprovacaoListView, CertificadoAprovacaoCreateView, PPEDeliveryListView,
    PPEDeliveryCreateView, delivery_sign_view, product_search_ajax, product_add_ajax,
    PPEMatrixCreateView, PPEMatrixUpdateView, ppe_matrix_toggle_active,
    PPEMatrixListView, PPEMatrixBulkCreateView, PPEMatrixBulkUpdateView, PPEMatrixBulkDeleteView,
    SectorPPEMatrixListView, SectorPPEMatrixEditView, SectorPPEMatrixActivateView, SectorPPEMatrixDeactivateView,
    SectorPPEMatrixCreateView, LegacyMatrixRedirectView,
    ca_consultar_ajax
)

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('add/', ProductCreateView.as_view(), name='product_create'),
    path('<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
    path('<int:pk>/edit/', ProductUpdateView.as_view(), name='product_update'),
    path('<int:product_pk>/variants/add/', ProductVariantCreateView.as_view(), name='variant_create'),
    
    path('ca/', CertificadoAprovacaoListView.as_view(), name='ca_list'),
    path('ca/add/', CertificadoAprovacaoCreateView.as_view(), name='ca_create'),
    path('ca/consultar_ajax/', ca_consultar_ajax, name='ca_consultar_ajax'),
    
    path('deliveries/', PPEDeliveryListView.as_view(), name='delivery_list'),
    path('deliveries/add/', PPEDeliveryCreateView.as_view(), name='delivery_create'),
    path('deliveries/<int:pk>/sign/', delivery_sign_view, name='delivery_sign'),
    
    path('add/ajax/', product_add_ajax, name='product_add_ajax'),
    path('search_ajax/', product_search_ajax, name='product_search_ajax'),
    
    path('matrix/add/<int:function_pk>/', LegacyMatrixRedirectView.as_view(), name='ppe_matrix_create'),
    path('matrix/<int:pk>/edit/', LegacyMatrixRedirectView.as_view(), name='ppe_matrix_update'),
    path('matrix/<int:pk>/toggle/', LegacyMatrixRedirectView.as_view(), name='ppe_matrix_toggle_active'),
    
    # Rotas da Matriz de EPI por Setor (Exclusiva)
    path('matrices/', SectorPPEMatrixListView.as_view(), name='sector_matrix_list'),
    path('matrices/add/', SectorPPEMatrixCreateView.as_view(), name='sector_matrix_create'),
    path('matrices/create/', SectorPPEMatrixCreateView.as_view()),
    path('matrices/bulk/', SectorPPEMatrixCreateView.as_view()),
    path('matrices/sector/<int:sector_pk>/edit/', SectorPPEMatrixEditView.as_view(), name='sector_matrix_edit'),
    path('matrices/sector/<int:sector_pk>/activate/', SectorPPEMatrixActivateView.as_view(), name='sector_matrix_activate'),
    path('matrices/sector/<int:sector_pk>/deactivate/', SectorPPEMatrixDeactivateView.as_view(), name='sector_matrix_deactivate'),

    # Redirecionamentos de compatibilidade para rotas legadas
    path('matrices/add-bulk/', SectorPPEMatrixCreateView.as_view(), name='matrix_bulk_create'),
    path('matrices/legacy-functions/', LegacyMatrixRedirectView.as_view(), name='matrix_list'),
    path('matrices/function/<int:function_pk>/edit/', LegacyMatrixRedirectView.as_view(), name='matrix_bulk_update'),
    path('matrices/function/<int:function_pk>/delete/', LegacyMatrixRedirectView.as_view(), name='matrix_bulk_delete'),
]


