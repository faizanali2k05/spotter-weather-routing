from datetime import datetime,timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET,require_POST
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from django.conf import settings
from .services import build_plan,geocode_place
@require_GET
def health(request):return JsonResponse({'status':'ok'})
@require_GET
def geocode(request):
    query=request.GET.get('q','').strip()
    if len(query)<2:return JsonResponse({'error':'Enter a location.'},status=400)
    try:return JsonResponse(geocode_place(query))
    except Exception as exc:return JsonResponse({'error':str(exc)},status=502)
logger=logging.getLogger(__name__)

@csrf_exempt
@require_POST
def plan(request):
    try:
        if len(request.body)>8192:raise ValueError('Request too large.')
        data=json.loads(request.body)
        origin=str(data.get('origin','')).strip();destination=str(data.get('destination','')).strip()
        if not 2<=len(origin)<=180 or not 2<=len(destination)<=180:raise ValueError('Origin and destination must be valid locations.')
        load=float(data.get('load_lbs',0));spacing=int(data.get('spacing_miles',25))
        if load<0 or load>100000:raise ValueError('Load must be between 0 and 100,000 lbs.')
        if spacing not in (10,25,50):raise ValueError('Checkpoint spacing must be 10, 25 or 50 miles.')
        departure=str(data['departure'])
        return JsonResponse(build_plan(origin,destination,departure,load,spacing))
    except (ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:return JsonResponse({'error':str(exc)},status=400)
    except Exception as exc:
        logger.exception('Route planning failed')
        message=f'{type(exc).__name__}: {exc}' if settings.DEBUG else 'Routing or weather provider unavailable. Please try again.'
        return JsonResponse({'error':message},status=502)
