from django.core.management.base import BaseCommand
from mobile_number.models import MobileNumber
import re
from mongoengine import connect, disconnect
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Final check to ensure the system is working as expected with manual data entry'

    def handle(self, *args, **options):
        # Step 1: Prompt for mobile number with validation
        while True:
            mobile_number = input("Please enter the mobile number (with country code, e.g., +911234567890): ")

            # Validate the mobile number format
            if re.match(r'^\+\d{1,3}\d{10}$', mobile_number):
                break
            else:
                self.stdout.write(self.style.ERROR("Invalid format. Please use the format +[country code][10 digit number]"))

        # Step 2: Connect to MongoDB and perform checks
        try:
            connect(
                db=os.getenv('MONGO_DB_NAME'),
                host=os.getenv('MOBILE_NUMBER_DB_URI'),
                alias="mobile_number",
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
                serverSelectionTimeoutMS=5000
            )
            self.stdout.write(self.style.SUCCESS('Successfully connected to MongoDB'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to connect to MongoDB: {str(e)}'))
            return

        # Step 3: Attempt to create an entry with the mobile number
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

        # Step 4: Disconnect MongoDB connection after the checks
        disconnect()

        self.stdout.write(self.style.SUCCESS('Final check completed successfully'))
