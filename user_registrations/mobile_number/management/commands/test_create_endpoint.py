from django.core.management.base import BaseCommand
import requests
import json
import re

class Command(BaseCommand):
    help = 'Test the mobile number creation endpoint with user input'

    def handle(self, *args, **options):
        url = 'http://127.0.0.1:8000/api/mobile_number/create/'

        # Get mobile number input from the user
        while True:
            mobile_number = input("Please enter the mobile number (with country code, e.g., +911234567890): ")
            
            # Validate the mobile number format
            if re.match(r'^\+\d{1,3}\d{10}$', mobile_number):
                break
            else:
                self.stdout.write(self.style.ERROR("Invalid format. Please use the format +[country code][10 digit number]"))

        # Prepare the payload with service_prefix included
        payload = {
            "mobile_number": mobile_number,
            "service_prefix": "SU"  # Explicitly provide service_prefix
        }
        headers = {'Content-Type': 'application/json'}

        # Send the HTTP POST request to the API
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        
        # Check the response status and provide feedback
        if response.status_code == 201:
            self.stdout.write(self.style.SUCCESS(f'Successfully created mobile number: {response.json()}'))
        else:
            self.stdout.write(self.style.ERROR(f'Failed to create mobile number: {response.status_code} {response.text}'))
