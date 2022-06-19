# -*- coding: utf-8 -*-

from django.http import JsonResponse


def health(request):
    return JsonResponse({"status": "ok"})


