from django.urls import path
from .views import (
    SupplierCreateView, FiscalNoteListView, FiscalNoteCreateView, FiscalNoteDetailView,
    LotCreateView, LotDeleteView, confirm_fiscal_note_view, StockTransferListView, StockTransferCreateView,
    StockTransferDetailView, StockTransferItemCreateView, expedite_transfer_view, receive_transfer_view
)

urlpatterns = [
    path('suppliers/add/', SupplierCreateView.as_view(), name='supplier_create'),
    path('nfs/', FiscalNoteListView.as_view(), name='fiscal_note_list'),
    path('nfs/add/', FiscalNoteCreateView.as_view(), name='fiscal_note_create'),
    path('nfs/<int:pk>/', FiscalNoteDetailView.as_view(), name='fiscal_note_detail'),
    path('nfs/<int:note_pk>/lots/add/', LotCreateView.as_view(), name='lot_create'),
    path('lots/<int:pk>/delete/', LotDeleteView.as_view(), name='lot_delete'),
    path('nfs/<int:pk>/confirm/', confirm_fiscal_note_view, name='fiscal_note_confirm'),
    
    path('transfers/', StockTransferListView.as_view(), name='transfer_list'),
    path('transfers/add/', StockTransferCreateView.as_view(), name='transfer_create'),
    path('transfers/<int:pk>/', StockTransferDetailView.as_view(), name='transfer_detail'),
    path('transfers/<int:transfer_pk>/items/add/', StockTransferItemCreateView.as_view(), name='transfer_item_create'),
    path('transfers/<int:pk>/expedite/', expedite_transfer_view, name='transfer_expedite'),
    path('transfers/<int:pk>/receive/', receive_transfer_view, name='transfer_receive'),
]
