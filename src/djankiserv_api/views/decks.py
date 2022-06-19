
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from djankiserv_unki.collection import Collection

@csrf_exempt
@api_view(["POST", "GET"])
def decks(request):
    with Collection(request.user.username, settings.DJANKISERV_DATA_ROOT) as col:
        return JsonResponse({"decks": col.decks.decks})


@csrf_exempt
@api_view(["POST", "GET"])
def decks_conf(request):
    with Collection(request.user.username, settings.DJANKISERV_DATA_ROOT) as col:
        return JsonResponse({"decks_conf": col.decks.dconf})


