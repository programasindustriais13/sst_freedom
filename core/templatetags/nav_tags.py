from django import template
from django.utils.safestring import mark_safe

register = template.Library()

def get_active_menu_item(request):
    if not request:
        return None

    path = getattr(request, 'path', '') or ''
    match = getattr(request, 'resolver_match', None)
    url_name = getattr(match, 'url_name', '') or ''

    # 1. Relatórios (deve ter precedência sobre outros prefixos)
    if path.startswith('/reports/') or url_name.startswith('report_'):
        return 'reports'

    # 2. Alertas / Notificações
    if path.startswith('/notifications/') or url_name.startswith('alert_'):
        return 'notifications'

    # 3. Entregas / Ficha EPI (dentro de /ppe/)
    if path.startswith('/ppe/deliveries/') or url_name.startswith('delivery_'):
        return 'deliveries'

    # 4. Matriz de EPI por Setor (dentro de /ppe/)
    if path.startswith('/ppe/matrices/') or 'sector_matrix' in url_name or 'matrix' in url_name:
        return 'matrices'

    # 5. EPIs / Catálogo (rotas de /ppe/ que não são entregas nem matrizes)
    if path.startswith('/ppe/') or url_name.startswith('product_'):
        return 'ppe'

    # 6. Colaboradores
    if path.startswith('/employees/') or url_name.startswith('employee_'):
        return 'employees'

    # 7. Estoque Mínimo
    if path.startswith('/inventory/minimum-stock/') or url_name == 'minimum_stock_list':
        return 'minimum_stock'

    # 8. Transferências de Estoque
    if path.startswith('/inventory/transfers/') or url_name.startswith('transfer_'):
        return 'transfers'

    # 9. Almoxarifado / Compras / NFs / Fornecedores
    if (
        path.startswith('/inventory/nfs/')
        or path.startswith('/inventory/suppliers/')
        or url_name.startswith('fiscal_note_')
        or url_name.startswith('supplier_')
    ):
        return 'nfs'

    # 10. Cadastros / Unidades / Organizações
    if path.startswith('/organizations/') or url_name.startswith('unit_') or url_name.startswith('sector_') or url_name == 'organization_dashboard':
        return 'organizations'

    # 11. Início / Dashboard
    if path == '/' or url_name == 'dashboard':
        return 'dashboard'

    return None


@register.simple_tag(takes_context=True)
def active_nav(context, item_name):
    """
    Retorna apenas a classe CSS 'active' se o item for o único item ativo do menu.
    """
    request = context.get('request')
    active_item = get_active_menu_item(request)
    if active_item == item_name:
        return 'active'
    return ''


@register.simple_tag(takes_context=True)
def nav_aria(context, item_name):
    """
    Retorna o atributo de acessibilidade aria-current="page" se o item for o único item ativo.
    """
    request = context.get('request')
    active_item = get_active_menu_item(request)
    if active_item == item_name:
        return mark_safe('aria-current="page"')
    return ''


@register.simple_tag(takes_context=True)
def is_nav_active(context, item_name):
    """
    Retorna apenas 'active' para classes CSS quando necessário.
    """
    request = context.get('request')
    active_item = get_active_menu_item(request)
    if active_item == item_name:
        return 'active'
    return ''
