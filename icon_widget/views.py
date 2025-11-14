# In icon_widget/views.py
import os
import requests
import uuid
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

@require_POST
@csrf_exempt
def download_icon_api(request):
    model = request.POST.get("model")
    icon_name = request.POST.get("icon")
    color = request.POST.get("color", "#000000")

    if not model or not icon_name:
        return HttpResponseBadRequest("Parametri 'model' e 'icon' richiesti.")

    if not (request.user.is_superuser or request.user.has_perm(f"{model.split('.')[0]}.change_{model.split('.')[1]}")):
        return JsonResponse({"error": "Not permitted"}, status=403)

    if color.startswith('#'):
        color = color.replace("#", "%23")

    svg_url = f"https://api.iconify.design/{icon_name}.svg"
    params = {'color': color}

    try:
        response = requests.get(svg_url, params=params, timeout=5)
        
        if response.status_code == 200:
            save_path_relative = os.path.join('icone', model.split('.')[1]) # Es. 'icone/punteggio'
            save_path_absolute = os.path.join(settings.MEDIA_ROOT, save_path_relative)
            
            os.makedirs(save_path_absolute, exist_ok=True)
            
            filename = f"icon-{uuid.uuid4()}.svg"
            file_path_absolute = os.path.join(save_path_absolute, filename)

            with open(file_path_absolute, "wb") as f:
                f.write(response.content)
            
            file_path_for_db = os.path.join(save_path_relative, filename)
            
            return JsonResponse({"path": file_path_for_db, "url": f"{settings.MEDIA_URL}{file_path_for_db}"})
        else:
            return JsonResponse(
                {"error": f"Failed to download SVG. Status: {response.reason}"},
                status=response.status_code
            )
    except Exception as e:
        return JsonResponse({"error": f"Internal server error: {e}"}, status=500)