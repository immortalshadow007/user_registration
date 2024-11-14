from django.apps import AppConfig
import logging as log

logger = log.getLogger(__name__)

class MobileNumberConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mobile_number'

    # Any startup tasks for the mobile_number app can be included here
    def ready(self):
        logger.info("MobileNumber App is ready.")


