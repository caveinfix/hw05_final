from django.conf import settings
from django.core.paginator import Paginator


def get_paginator(request, queryset):
    paginator = Paginator(queryset, settings.PAGE_SIZE)
    page_number = request.GET.get("page")
    return paginator.get_page(page_number)
