# -*- coding: utf-8 -*-

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser

from djankiserv.unki.collection import Collection


@csrf_exempt
@api_view(["POST"])
@parser_classes([JSONParser])
def add_notes(request):
    with Collection(request.user.username, settings.DJANKISERV_DATA_ROOT) as col:
        note_ids = []
        for note in request.data["notes"]:
            note_ids.append(col.create_note(note, deck_name=request.data["deck"]))

    return JsonResponse({"note_ids": note_ids})


@csrf_exempt
@api_view(["POST", "GET"])
@parser_classes([JSONParser])
def notes(request):
    with Collection(request.user.username, settings.DJANKISERV_DATA_ROOT) as col:
        notes = col.get_notes(request.data.get("ids"))

    return JsonResponse({"notes": [n.as_dict() for n in notes]})


@csrf_exempt
@api_view(["POST"])
@parser_classes([JSONParser])
def delete_notes(request):
    with Collection(request.user.username, settings.DJANKISERV_DATA_ROOT) as col:
        note_ids = request.data.get("ids")
        if not note_ids:  # is this a little dangerous maybe?
            note_ids = col.all_note_ids()
        col.rem_notes(note_ids)

    return JsonResponse({"status": "ok"})


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


@csrf_exempt
@api_view(["POST", "GET"])
def tags(request):
    with Collection(request.user.username, settings.DJANKISERV_DATA_ROOT) as col:
        return JsonResponse({"tags": list(col.tags.keys())})


@csrf_exempt
@api_view(["POST", "GET"])
def models(request):
    with Collection(request.user.username, settings.DJANKISERV_DATA_ROOT) as col:
        return JsonResponse({"models": col.models.models})
