from .build_info import get_build_info


def build_info(_request):
    """
    Rende disponibile `KOR35_BUILD` in tutti i template (inclusa Django admin).
    """
    return {"KOR35_BUILD": get_build_info()}

