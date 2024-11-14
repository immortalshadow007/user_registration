from django.core.management.base import BaseCommand
from mobile_number.models import MobileNumber
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import os

class Command(BaseCommand):
    help = 'Retrieve and decrypt entries from MongoDB'

    key_cache = {}

    def get_encryption_key(self, entry_id):
        if entry_id in self.key_cache:
            return self.key_cache[entry_id]

        kv_uri = os.getenv("AZURE_KEY_VAULT_URI")
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=kv_uri, credential=credential)

        key_name = f"encryption-key-{entry_id}"
        secret = client.get_secret(key_name)
        encryption_key = bytes.fromhex(secret.value)

        # Cache the key for future use
        self.key_cache[entry_id] = encryption_key

        return encryption_key

    def decrypt_mobile_number(self, encrypted_mobile_number, encryption_key):
        encrypted_data = base64.b64decode(encrypted_mobile_number)
        iv = encrypted_data[:16]
        cipher = Cipher(algorithms.AES(encryption_key), modes.CFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_mobile_number = decryptor.update(encrypted_data[16:]) + decryptor.finalize()
        return decrypted_mobile_number.decode('utf-8')

    def handle(self, *args, **options):
        entries = MobileNumber.objects.all()
        
        if not entries:
            self.stdout.write(self.style.WARNING('No entries found in the database.'))
        else:
            for entry in entries:
                try:
                    # Fetch the encryption key using the cached method
                    encryption_key = self.get_encryption_key(entry._id)

                    # Decrypt the mobile number
                    decrypted_mobile_number = self.decrypt_mobile_number(entry.mobile_number, encryption_key)

                    self.stdout.write(f'ID: {entry._id}')
                    self.stdout.write(f'Mobile Number (Decrypted): {decrypted_mobile_number}')
                    self.stdout.write(f'Service Prefix: {entry.service_prefix}')
                    self.stdout.write(f'Created At: {entry.created_at}')
                    self.stdout.write(f'Expiry At: {entry.expiry_at}')
                    self.stdout.write(f'Is Verified: {entry.is_verified}')
                    self.stdout.write('-' * 50)
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to decrypt mobile number for entry ID {entry._id}: {str(e)}"))
                    self.stdout.write('-' * 50)
