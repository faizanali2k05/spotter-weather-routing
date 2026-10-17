import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError as DRFValidationError

logger = logging.getLogger('spotter.routing')


class SpotterBaseException(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = 'INTERNAL_ERROR'
    default_message = 'An unexpected error occurred in route planning.'

    def __init__(self, message=None, code=None, status_code=None, details=None):
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.code = code or self.default_code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}


class GeocodingError(SpotterBaseException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = 'GEOCODING_ERROR'
    default_message = 'Failed to geocode location.'


class LocationNotFoundError(SpotterBaseException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'LOCATION_NOT_FOUND'
    default_message = 'Specified location could not be found.'


class RouteNotFoundError(SpotterBaseException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'ROUTE_NOT_FOUND'
    default_message = 'No drivable route found between the specified locations.'


class ProviderTimeoutError(SpotterBaseException):
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_code = 'PROVIDER_TIMEOUT'
    default_message = 'Routing or weather provider request timed out.'


class ProviderRateLimitError(SpotterBaseException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = 'PROVIDER_RATE_LIMIT'
    default_message = 'External provider rate limit reached. Please wait before retrying.'


class ForecastHorizonError(SpotterBaseException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'FORECAST_HORIZON_EXCEEDED'
    default_message = 'Departure or checkpoint arrival time falls outside the supported 48-hour forecast horizon.'


class MalformedProviderResponseError(SpotterBaseException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = 'PROVIDER_MALFORMED_RESPONSE'
    default_message = 'External service returned an invalid or malformed response.'


class ProviderNetworkError(SpotterBaseException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = 'PROVIDER_NETWORK_ERROR'
    default_message = 'Unable to establish network connection with external routing or weather service.'


class InputValidationError(SpotterBaseException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'VALIDATION_ERROR'
    default_message = 'Invalid request parameters.'


def custom_exception_handler(exc, context):
    """
    Standardized DRF exception handler returning predictable JSON error schemas:
    {
        "error": "Human-readable message",
        "code": "ERROR_CODE",
        "details": {}
    }
    """
    # First let DRF handle its own exceptions (validation, 404, not authenticated, etc.)
    response = exception_handler(exc, context)

    if isinstance(exc, SpotterBaseException):
        logger.warning(
            "Spotter app exception [%s] code=%s: %s (details=%s)",
            exc.__class__.__name__, exc.code, exc.message, exc.details
        )
        return Response({
            'error': exc.message,
            'code': exc.code,
            'details': exc.details,
        }, status=exc.status_code)

    if response is not None:
        error_msg = 'Validation error'
        if isinstance(exc, DRFValidationError):
            if isinstance(response.data, dict):
                first_key = next(iter(response.data))
                val = response.data[first_key]
                if isinstance(val, list) and val:
                    error_msg = f"{first_key}: {val[0]}"
                else:
                    error_msg = f"{first_key}: {val}"
            elif isinstance(response.data, list) and response.data:
                error_msg = str(response.data[0])
        elif 'detail' in response.data:
            error_msg = str(response.data['detail'])

        return Response({
            'error': error_msg,
            'code': getattr(exc, 'default_code', 'REQUEST_ERROR').upper(),
            'details': response.data if isinstance(response.data, dict) else {'errors': response.data},
        }, status=response.status_code)

    # Unhandled server errors
    logger.exception("Unhandled server exception during request: %s", exc)
    return Response({
        'error': 'Internal server error occurred while processing route plan.',
        'code': 'INTERNAL_SERVER_ERROR',
        'details': {},
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
