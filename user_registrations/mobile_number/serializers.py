from rest_framework_mongoengine.serializers import DocumentSerializer
from .models import MobileNumber

class MobileNumberSerializer(DocumentSerializer):
    class Meta:
        model = MobileNumber
        fields = ['mobile_number']

