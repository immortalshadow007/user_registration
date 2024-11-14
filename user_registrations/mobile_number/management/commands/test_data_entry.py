from django.core.management.base import BaseCommand
from mobile_number.models import MobileNumber
import re

class Command(BaseCommand):
    help = 'Test manual data entry into MongoDB'

    def handle(self, *args, **options):
        while True:
            mobile_number = input("Please enter the mobile number (with country code, e.g., +911234567890): ")
            
            # Validate the mobile number format
            if re.match(r'^\+\d{1,3}\d{10}$', mobile_number):
                break
            else:
                self.stdout.write(self.style.ERROR("Invalid format. Please use the format +[country code][10 digit number]"))
        
        try:
            entry = MobileNumber.create_entry(mobile_number)
            self.stdout.write(self.style.SUCCESS(f'Successfully created entry with ID: {entry._id}'))
            self.stdout.write(f'Mobile Number: {entry.mobile_number}')
            self.stdout.write(f'Service Prefix: {entry.service_prefix}')
            self.stdout.write(f'Created At: {entry.created_at}')
            self.stdout.write(f'Expiry At: {entry.expiry_at}')
            self.stdout.write(f'Is Verified: {entry.is_verified}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create entry: {str(e)}'))