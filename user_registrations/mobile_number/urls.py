from django.urls import path
from .views import MobileNumberCreateView

urlpatterns = [
    path('create/', MobileNumberCreateView.as_view(), name='mobile_number_create'),
]
