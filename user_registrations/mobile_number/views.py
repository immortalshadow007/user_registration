from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import MobileNumber, VerificationRequestLog
from .serializers import MobileNumberSerializer
import logging
import requests
import os
import threading

logger = logging.getLogger(__name__)

class MobileNumberCreateView(APIView):
    """
    View to create a mobile number entry in the database.
    """

    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get('mobile_number')

        # Check if the user profile already exists
        if MobileNumber.check_user_profile_exists(mobile_number):
            return Response({'error': 'User already registered. Please log in.'}, status=status.HTTP_409_CONFLICT)

        # Check if the rate limit has been exceeded
        request_count = VerificationRequestLog.count_requests(mobile_number)
        if request_count >= 10:
            return Response({'error': 'Rate limit exceeded. Try again after 24 hours.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Log the OTP request
        VerificationRequestLog.log_request(mobile_number)

        # Serialize the incoming data
        serializer = MobileNumberSerializer(data=request.data)
        if serializer.is_valid():
            mobile_number = serializer.validated_data['mobile_number']
            entry = MobileNumber.create_entry(mobile_number)

            # Trigger the OTP management asynchronously using threading
            threading.Thread(target=self.trigger_otp_management, args=(entry.mobile_number,entry._id)).start()

            return Response({
                'id': entry._id,
                'mobile_number': entry.mobile_number,
                'service_prefix': entry.service_prefix,
                'created_at': entry.created_at,
                'expiry_at': entry.expiry_at,
                'is_verified': entry.is_verified
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def trigger_otp_management(self, encrypted_mobile_number, document_id):
        """
        This method triggers the OtpManagementView to send the encrypted mobile number
        to the OTP management service.
        """
        try:
            # Define the OTP management API URL
            api_url = os.getenv("OTP_MANAGEMENT_API_URL")
            api_key = os.getenv("OTP_MANAGEMENT_API_KEY")

            # Prepare the payload
            payload = {
                'document_id': document_id,
                'encrypted_mobile_number': encrypted_mobile_number
            }

            # Prepare headers
            headers = {
                'M-API-KEY': api_key,
                'Content-Type': 'application/json'
            }

            # Send the request to OTP management
            response = requests.post(api_url, json=payload, headers=headers)

            if response.status_code != 200:
                logger.error(f"Failed to initiate OTP generation: {response.status_code}")

        except requests.RequestException as e:
            logger.error(f"Failed to send data to OTP management service: {str(e)}")


