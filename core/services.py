import json
from django.db import transaction
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from audit.models import log_audit, log_action

_generic_fields = None

def get_generic_fields():
    """
    Cache and return all fields in the project that are GenericForeignKey.
    """
    global _generic_fields
    if _generic_fields is not None:
        return _generic_fields
    _generic_fields = []
    for model in apps.get_models():
        for field in model._meta.private_fields:
            if isinstance(field, GenericForeignKey):
                _generic_fields.append((model, field))
        for field in model._meta.get_fields():
            if isinstance(field, GenericForeignKey) and (model, field) not in _generic_fields:
                _generic_fields.append((model, field))
    return _generic_fields


def collect_dependencies(start_objs):
    """
    Recursively collect all database records that point to start_objs
    (either directly or indirectly).
    
    Returns:
        dict: A dictionary mapping model_class -> {pk: instance}
    """
    if not isinstance(start_objs, (list, tuple, set)):
        if hasattr(start_objs, '__iter__'):
            start_objs = list(start_objs)
        else:
            start_objs = [start_objs]

    collected = {}
    to_process = list(start_objs)
    visited = set()

    for obj in start_objs:
        if obj is None:
            continue
        key = (obj.__class__, obj.pk)
        visited.add(key)
        if obj.__class__ not in collected:
            collected[obj.__class__] = {}
        collected[obj.__class__][obj.pk] = obj

    index = 0
    while index < len(to_process):
        obj = to_process[index]
        index += 1

        if obj is None:
            continue

        # 1. Standard incoming relations (ForeignKeys, OneToOne, etc.)
        for relation in obj._meta.related_objects:
            related_model = relation.related_model
            remote_field = relation.remote_field

            # Query all related instances pointing to this object
            filter_kwargs = {remote_field.name: obj}
            for rel_obj in related_model.objects.filter(**filter_kwargs):
                key = (rel_obj.__class__, rel_obj.pk)
                if key not in visited:
                    visited.add(key)
                    if rel_obj.__class__ not in collected:
                        collected[rel_obj.__class__] = {}
                    collected[rel_obj.__class__][rel_obj.pk] = rel_obj
                    to_process.append(rel_obj)

        # 2. Generic relations pointing to this object (e.g., Alert)
        content_type = ContentType.objects.get_for_model(obj)
        for gen_model, gen_field in get_generic_fields():
            filter_kwargs = {
                gen_field.ct_field: content_type,
                gen_field.fk_field: obj.pk
            }
            for rel_obj in gen_model.objects.filter(**filter_kwargs):
                key = (rel_obj.__class__, rel_obj.pk)
                if key not in visited:
                    visited.add(key)
                    if rel_obj.__class__ not in collected:
                        collected[rel_obj.__class__] = {}
                    collected[rel_obj.__class__][rel_obj.pk] = rel_obj
                    to_process.append(rel_obj)

    return collected


def topological_sort_models(models_set):
    """
    Sort models topologically based on their ForeignKey relationships.
    If model A has a foreign key to model B, A must come BEFORE B in the sort list,
    meaning we delete instances of A before deleting instances of B.
    """
    adj = {m: set() for m in models_set}
    in_degree = {m: 0 for m in models_set}

    for m in models_set:
        for field in m._meta.get_fields():
            if field.is_relation and field.many_to_one and not field.auto_created:
                related_model = field.related_model
                if related_model in models_set and related_model != m:
                    if related_model not in adj[m]:
                        adj[m].add(related_model)
                        in_degree[related_model] += 1

    queue = [m for m in models_set if in_degree[m] == 0]
    order = []

    while queue:
        # Sort queue by name to ensure stable, deterministic ordering
        queue.sort(key=lambda x: x.__name__)
        u = queue.pop(0)
        order.append(u)

        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    if len(order) < len(models_set):
        remaining = models_set - set(order)
        order.extend(list(remaining))

    return order


@transaction.atomic
def execute_cascade_delete(objs, request=None, user=None):
    """
    Executes a cascade deletion of the given objects and all their dependencies.
    Wraps everything in transaction.atomic().
    Logs the action in AuditLog.
    """
    if not isinstance(objs, (list, tuple, set)):
        if hasattr(objs, '__iter__'):
            objs = list(objs)
        else:
            objs = [objs]

    if not objs:
        return 0

    # 1. Collect all dependencies (ensuring fresh DB state)
    collected = collect_dependencies(objs)

    # 2. Build audit representation before deletion
    audit_summary = {}
    total_deleted = 0
    for model_class, inst_dict in collected.items():
        model_label = f"{model_class._meta.app_label}.{model_class.__name__}"
        audit_summary[model_label] = [
            {"id": pk, "str": str(inst)} for pk, inst in inst_dict.items()
        ]
        total_deleted += len(inst_dict)

    changes_before_json = json.dumps(audit_summary, indent=2, ensure_ascii=False)

    # 3. Log audit BEFORE deleting so we can record the action details
    primary_obj = objs[0]
    action_msg = f"Exclusão em Cascata Administrativa: {len(objs)} objeto(s) principal(is) e dependências"
    
    if request:
        log_audit(
            request=request,
            action=action_msg,
            model_name=primary_obj.__class__.__name__,
            object_id=primary_obj.pk,
            before=changes_before_json,
            after="Deletado com sucesso"
        )
    else:
        log_action(
            user=user,
            action=action_msg,
            model_name=primary_obj.__class__.__name__,
            object_id=primary_obj.pk,
            before=changes_before_json,
            after="Deletado com sucesso"
        )

    # 4. Sort model classes topologically (leaves first, roots last)
    sorted_models = topological_sort_models(set(collected.keys()))

    # 5. Delete in reverse topological order (or sorted order, since topological_sort already puts dependencies first)
    # If A points to B, A comes before B, so we delete A first.
    for model_class in sorted_models:
        instances = list(collected[model_class].values())
        pks = [inst.pk for inst in instances]

        # Handle potential self-referential relations (e.g. parent category pointing to parent category)
        self_fk_fields = []
        for field in model_class._meta.get_fields():
            if field.is_relation and field.many_to_one and field.related_model == model_class:
                self_fk_fields.append(field)

        if self_fk_fields:
            for field in self_fk_fields:
                if field.null:
                    model_class.objects.filter(pk__in=pks).update(**{field.name: None})

        # Execute bulk deletion
        model_class.objects.filter(pk__in=pks).delete()

    return total_deleted
