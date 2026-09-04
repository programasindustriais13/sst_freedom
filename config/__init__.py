# Compatibilidade com Python 3.14: no Python 3.14, copy(super()) em BaseContext.__copy__
# copia o objeto super() em vez de instanciar a classe derivada, gerando AttributeError em testes com templates.
try:
    import django.template.context as _django_context
    def _patched_base_context_copy(self):
        duplicate = self.__class__.__new__(self.__class__)
        duplicate.__dict__.update(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate
    _django_context.BaseContext.__copy__ = _patched_base_context_copy
except Exception:
    pass
