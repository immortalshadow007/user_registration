import os
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

class APIKeyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        api_key = request.headers.get('X-API-KEY')

        # Check if the API key is present in the request
        if not api_key:
            return JsonResponse({'error': 'API key is missing'}, status=401)

        # Load the API keys from the environment
        valid_keys = [
            os.getenv('PRIMARY_API_KEY'),
            os.getenv('SECONDARY_API_KEY')
        ]

        # Check if the provided API key is valid
        if api_key not in valid_keys:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        # If the key is valid, allow the request to proceed
        return None
