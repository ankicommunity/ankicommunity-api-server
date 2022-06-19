
from urllib import response
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from djankiserv_unki.collection import Collection

@csrf_exempt
@api_view(["GET"])
def get_decks(request):
    decks = None
    with Collection(request.user.username, settings.DJANKISERV_DATA_ROOT) as col:
        decks = [value for key, value in dict(col.decks.decks).items()]

    response = {}
    response['pagination'] = {}
    response["pagination"]['count'] = len(decks)
    response['decks'] = decks
    return JsonResponse(response)


@csrf_exempt
@api_view(["GET"])
def get_deck_confs(request):
    conf = None
    with Collection(request.user.username, settings.DJANKISERV_DATA_ROOT) as col:
        conf = [value for key, value in dict(col.decks.dconf).items()]

    response = {}
    response['pagination'] = {}
    response['pagination']['count'] = len(conf)
    response['decksConf'] = conf
    return JsonResponse(response)


