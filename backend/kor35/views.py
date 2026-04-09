from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .build_info import get_build_info


@api_view(["GET"])
@permission_classes([AllowAny])
def version(_request):
    """
    Endpoint leggero per debug/versioning.
    Utile anche per capire se frontend/backend sono allineati.
    """
    return Response({"backend": get_build_info()})

