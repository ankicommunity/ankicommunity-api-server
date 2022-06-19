
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from djankiserv_unki.collection import Collection

@csrf_exempt
@api_view(["POST", "GET"])
def models(request):
    with Collection(request.user.username, settings.DJANKISERV_DATA_ROOT) as col:
        return JsonResponse({"models": col.models.models})
