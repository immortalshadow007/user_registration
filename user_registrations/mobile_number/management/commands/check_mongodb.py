from django.core.management.base import BaseCommand
from mongoengine import connect
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Checks the connection to MongoDB'

    def handle(self, *args, **options):
        try:
            connect(
                db=settings.MONGO_DB_NAME,
                host=settings.MOBILE_NUMBER_DB_URI,
                alias="default"
            )
            self.stdout.write(self.style.SUCCESS('Successfully connected to MongoDB'))
            logger.info("Successfully connected to MongoDB from check_mongodb command")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to connect to MongoDB: {str(e)}'))
            logger.error(f"Failed to connect to MongoDB from check_mongodb command: {str(e)}")