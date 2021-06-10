from functools import lru_cache, wraps

import graphene
from django.conf import settings
from graphql import ResolveInfo


class PageNode(graphene.ObjectType):
    node_type = None
    total_count = graphene.Int()
    result_count = graphene.Int()
    offset = graphene.Int()
    limit = graphene.Int()

    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop("queryset", None)
        offset = kwargs.pop("offset", 0)
        limit = kwargs.pop("limit", settings.GRAPHENE_PER_PAGE)
        if queryset is None:
            queryset = self.node_type._meta.model.objects.all()
        total_count = queryset.count()
        if offset:
            queryset = queryset[offset:]
        if limit:
            queryset = queryset[:limit]
        result_count = queryset.count()
        super(PageNode, self).__init__(
            total_count=total_count,
            result_count=result_count,
            offset=offset,
            limit=limit,
            results=queryset,
        )


@lru_cache(maxsize=None)
def page_node_factory(node_type):
    name = f"{node_type.__name__}Page"
    return type(
        name,
        (PageNode,),
        {
            "results": graphene.List(node_type),
            "node_type": node_type,
        },
    )


def page_field_factory(node_type, **extra_kwargs):
    return graphene.Field(
        page_node_factory(node_type),
        offset=graphene.Int(required=False),
        limit=graphene.Int(required=False),
        **extra_kwargs,
    )


def resolve_page(resolver_function):
    @wraps(resolver_function)
    def page_resolver(self, info: ResolveInfo, **kwargs):
        queryset = resolver_function(self, info, **kwargs)
        return info.return_type.graphene_type(queryset=queryset, **kwargs)

    return page_resolver
