from django.core.management.base import BaseCommand
from mobile_number.models import APIKeyManager

class Command(BaseCommand):
    help = 'Generate and save API keys for the mobile number service.'

    def handle(self, *args, **kwargs):
        try:
            primary_key, secondary_key = APIKeyManager.generate_api_keys()
            self.stdout.write(self.style.SUCCESS('API keys generated successfully!'))
            self.stdout.write(f'Primary API Key: {primary_key}')
            self.stdout.write(f'Secondary API Key: {secondary_key}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error generating API keys: {str(e)}'))
