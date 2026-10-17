import logging
from datetime import datetime, timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .serializers import GeocodeQuerySerializer, PlanRequestSerializer
from .geocoding import geocode_place
from .services import build_plan

logger = logging.getLogger('spotter.views')


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    """
    Service health check endpoint.
    Returns status, version, and server timestamp.
    """
    return Response({
        'status': 'ok',
        'service': 'spotter-weather-routing-api',
        'version': '2.0.0',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'routing_provider': 'OSRM (Demo)',
        'weather_provider': 'Open-Meteo',
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def geocode(request):
    """
    Geocode location query string into structured coordinates.
    Query parameter: ?q=<location_name>
    """
    serializer = GeocodeQuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)

    query = serializer.validated_data['q']
    location = geocode_place(query)
    return Response(location, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def plan(request):
    """
    Calculate weather-aware route alternatives and risk exposure.
    Payload:
    {
        "origin": "New York, NY",
        "destination": "Philadelphia, PA",
        "departure": "2026-10-18T10:00:00Z",
        "load_lbs": 35000,
        "spacing_miles": 25
    }
    """
    serializer = PlanRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    origin = data['origin']
    destination = data['destination']
    departure = data['departure'].isoformat()
    load_lbs = data['load_lbs']
    spacing_miles = data['spacing_miles']

    result = build_plan(
        origin_text=origin,
        destination_text=destination,
        departure_str=departure,
        load_lbs=load_lbs,
        spacing_miles=spacing_miles,
    )

    return Response(result, status=status.HTTP_200_OK)
