"""
Constantes e Catálogo Canônico de Tamanhos e Unidades de Medida para o SST Freedom.
Centraliza as escolhas de domínio para evitar dispersão de regras em formulários ou views.
"""

# Unidades de Medida Padronizadas
UNIDADE_MEDIDA_CHOICES = (
    ('UND', 'UND — Unidade'),
    ('PAR', 'PAR — Par'),
    ('CX', 'CX — Caixa'),
    ('PCT', 'PCT — Pacote'),
    ('KIT', 'KIT — Kit'),
    ('CJ', 'CJ — Conjunto'),
    ('M', 'M — Metro'),
)

UNIDADE_MEDIDA_PADRAO = 'UND'

# Mapeamento de sinônimos e grafias equivalentes
UNIDADE_MEDIDA_SINONIMOS = {
    'UND': 'UND',
    'UN': 'UND',
    'UNID': 'UND',
    'UNIDADE': 'UND',
    'UNIDADES': 'UND',
    'PAR': 'PAR',
    'PARES': 'PAR',
    'CX': 'CX',
    'CAIXA': 'CX',
    'CAIXAS': 'CX',
    'PCT': 'PCT',
    'PACOTE': 'PCT',
    'PACOTES': 'PCT',
    'KIT': 'KIT',
    'KITS': 'KIT',
    'CJ': 'CJ',
    'CONJUNTO': 'CJ',
    'CONJUNTOS': 'CJ',
    'M': 'M',
    'METRO': 'M',
    'METROS': 'M',
}

def normalize_unit_of_measure(value: str) -> str:
    """
    Normaliza a entrada de unidade de medida para o código canônico.
    Se não for reconhecida, retorna o valor padrão 'UND' ou o próprio valor em maiúsculas.
    """
    if not value:
        return UNIDADE_MEDIDA_PADRAO
    val_clean = str(value).strip().upper()
    return UNIDADE_MEDIDA_SINONIMOS.get(val_clean, val_clean)


# Código canônico para Tamanho Único
TAMANHO_UNICO = 'U'
TAMANHO_UNICO_LABEL = 'Único'

# Catálogo Canônico de Tamanhos por Grupos
CANONICAL_SIZES_BY_GROUP = [
    {
        'grupo': 'Letras',
        'titulo': 'Tamanhos por Letras (Vestuário, Proteção Geral)',
        'tamanhos': ['PP', 'P', 'M', 'G', 'GG', 'XG', 'XXG']
    },
    {
        'grupo': 'Luvas',
        'titulo': 'Numeração de Luvas',
        'tamanhos': ['6', '7', '8', '9', '10', '11', '12']
    },
    {
        'grupo': 'Calçados',
        'titulo': 'Numeração de Calçados / Botinas',
        'tamanhos': [str(n) for n in range(34, 47)]
    }
]

# Todos os tamanhos permitidos no catálogo
ALL_CANONICAL_SIZES = set()
for grp in CANONICAL_SIZES_BY_GROUP:
    ALL_CANONICAL_SIZES.update(grp['tamanhos'])
ALL_CANONICAL_SIZES.add(TAMANHO_UNICO)

# Mapa de ordenação lógica para exibição consistente
_ORDER_MAP = {
    'U': 0,
    'PP': 1, 'P': 2, 'M': 3, 'G': 4, 'GG': 5, 'XG': 6, 'XXG': 7,
}
for idx, size in enumerate(['6', '7', '8', '9', '10', '11', '12'], start=10):
    _ORDER_MAP[size] = idx
for idx, size in enumerate([str(n) for n in range(34, 47)], start=30):
    _ORDER_MAP[size] = idx

def get_size_sort_key(size_str: str) -> int:
    """
    Retorna a chave numérica de ordenação lógica do tamanho.
    Tamanhos não mapeados recebem peso 999.
    """
    from ppe.services import canonical_size_key
    key = canonical_size_key(size_str)
    return _ORDER_MAP.get(key, 999)
