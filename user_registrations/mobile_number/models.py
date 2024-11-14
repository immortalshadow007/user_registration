from django.db import models
from mongoengine import Document, StringField, DateTimeField, get_connection
from django.conf import settings
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from pymongo import MongoClient
import hashlib
import random
import string
import logging as log
import base64
import os
import threading

# Initialize logging
logger = log.getLogger(__name__)

class MobileNumber(Document):
    _id = StringField(primary_key=True)
    mobile_number = StringField(required=True)
    mobile_number_hash = StringField(required=True)
    service_prefix = StringField(required=True)
    created_at = DateTimeField(default=datetime.now(timezone.utc))
    expiry_at = DateTimeField()
    is_verified = StringField(default="Not verified")

    meta = {
        'collection': 'user_auth_database',
        'db_alias': 'default',
        'timeseries': {
            'timeField': 'created_at',
            'metaField': 'service_prefix',
        },
        'indexes': [
            {
                'fields': ['expiry_at'],
                'expireAfterSeconds': 600,
            },
            {
                'fields': ['mobile_number'],
            },
            {
                'fields': ['mobile_number_hash'],
            },
            {
                'fields': ['is_verified'],
            }
        ]
    }

    @classmethod
    def generate_custom_id(cls, mobile_number):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        hashed_number = hashlib.md5(mobile_number.encode()).hexdigest()[:10]
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"UR-{timestamp}-{hashed_number}-{random_suffix}"

    @classmethod
    def encrypt_mobile_number(cls, mobile_number, encryption_key):
        # Encrypt the mobile number
        iv = os.urandom(16)  # Initialization vector
        cipher = Cipher(algorithms.AES(encryption_key), modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted_mobile_number = encryptor.update(mobile_number.encode()) + encryptor.finalize()

        # Return the encrypted mobile number as a base64 encoded string
        return base64.b64encode(iv + encrypted_mobile_number).decode('utf-8')

    @classmethod
    def store_encryption_key(cls, key_name, encryption_key, expiry_at):
        try:
            kv_uri = os.getenv("AZURE_KEY_VAULT_URI")
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=kv_uri, credential=credential)

            # Store the encryption key in Azure Key Vault
            client.set_secret(key_name, encryption_key.hex(), expires_on=expiry_at)
        except Exception as e:
            logger.error(f"Failed to store encryption key in Azure Key Vault.")
            raise

    @classmethod
    def hash_mobile_number(cls, mobile_number):
        """Creates a hash of the mobile number for lookup."""
        return hashlib.sha256(mobile_number.encode()).hexdigest()

    @classmethod
    def delete_existing_entry(cls, mobile_number):
        # Find the existing entry by mobile number
        mobile_number_hash = cls.hash_mobile_number(mobile_number)
        existing_entry = cls.objects(mobile_number_hash=mobile_number_hash).first()

        if existing_entry:
            def async_delete():
                try:
                    # Delete the associated encryption key from Azure Key Vault
                    kv_uri = os.getenv("AZURE_KEY_VAULT_URI")
                    credential = DefaultAzureCredential()
                    client = SecretClient(vault_url=kv_uri, credential=credential)

                    key_name = f"encryption-key-{existing_entry._id}"
                    client.begin_delete_secret(key_name)  # Initiates the deletion of the secret

                    # Delete the entry from MongoDB
                    existing_entry.delete()
                except Exception as e:
                    logger.error(f"Failed to delete existing entry or encryption key")
                    raise
            
            delete_thread = threading.Thread(target=async_delete)
            delete_thread.start()

    @classmethod
    def check_user_profile_exists(cls, mobile_number):
        """
        Check if the user profile already exists in the User_Profile_db based on the hashed mobile number.
        """
        try:
            # Hash the mobile number for lookup using the existing method
            mobile_number_hash = cls.hash_mobile_number(mobile_number)

            # Query the User_Profile_db directly for the hashed mobile number
            user_profile = cls._get_user_profile_db().find_one({"mobile_number_hash": mobile_number_hash})

            if user_profile:
                return True
            return False
        except Exception as e:
            logger.error(f"Error while checking if user profile exists: {str(e)}")
            raise

    @classmethod
    def _get_user_profile_db(cls):
        """
        Get the User_Profile_db collection from MongoDB. Replace this with actual MongoDB connection logic.
        """
        # Replace the below line with your MongoDB connection logic
        client = MongoClient(os.getenv("MONGO_DB_URI"))
        db = client["user-profiles"]
        return db["User_Profile_db"]

    @classmethod
    def create_entry(cls, mobile_number):
        # Delete any existing entry for the same mobile number
        cls.delete_existing_entry(mobile_number)

        # Generate a new encryption key
        encryption_key = os.urandom(32)  # 256-bit key

        # Encrypt the mobile number immediately
        encrypted_mobile_number = cls.encrypt_mobile_number(mobile_number, encryption_key)

        # Create the hash of the mobile number for lookup
        mobile_number_hash = cls.hash_mobile_number(mobile_number)

        # Create the custom ID
        custom_id = cls.generate_custom_id(encrypted_mobile_number)
        created_at = datetime.now(timezone.utc)
        expiry_at = created_at + timedelta(seconds=600)

        # Create the document to be stored
        entry = cls(
            _id=custom_id,
            mobile_number=encrypted_mobile_number,
            mobile_number_hash=mobile_number_hash,
            service_prefix="UR",
            created_at=created_at,
            expiry_at=expiry_at
        )

        # Use threading to store the encryption key and the document in parallel
        def store_data():
            try:
                # Store the encryption key in Azure Key Vault
                key_name = f"encryption-key-{custom_id}"
                cls.store_encryption_key(key_name, encryption_key, expiry_at)

                entry.save()
            except Exception as e:
                logger.error(f"Failed to store data: {str(e)}")
                raise

        # Start the thread to perform parallel storage
        thread = threading.Thread(target=store_data)
        thread.start()

        return entry

class VerificationRequestLog(Document):
    mobile_number_hash = StringField(required=True)
    requested_at = DateTimeField(default=datetime.now(timezone.utc))

    meta = {
        'collection': 'verification_request_log',
        'indexes': [
            {
                'fields': ['mobile_number_hash'],
            },
            {
                'fields': ['requested_at'],
                'expireAfterSeconds': 86400,
            }
        ]
    }

    @classmethod
    def count_requests(cls, mobile_number):
        # Hash the mobile number for lookup
        mobile_number_hash = MobileNumber.hash_mobile_number(mobile_number)
        
        # Calculate the time limit (last 24 hours)
        time_limit = datetime.now(timezone.utc) - timedelta(hours=24)

        # Count the number of requests in the last 24 hours
        return cls.objects(mobile_number_hash=mobile_number_hash, requested_at__gte=time_limit).count()

    @classmethod
    def log_request(cls, mobile_number):
        # Hash the mobile number before storing
        mobile_number_hash = MobileNumber.hash_mobile_number(mobile_number)

        # Create and save the OTP request log entry
        cls(mobile_number_hash=mobile_number_hash).save()