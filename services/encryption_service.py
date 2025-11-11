# services/encryption_service.py
import os
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from dotenv import load_dotenv

load_dotenv()

ENCRYPTION_KEY = os.getenv("RAZORPAY_ENCRYPTION_KEY", "fN7gMtVJjyiVqxTumwRoDqU0rSWo54Lt8jRzUgoAk4A=")

class EncryptionService:
    """
    AES encryption/decryption compatible with CryptoJS on frontend.
    """
    
    @staticmethod
    def decrypt_aes(ciphertext: str) -> str:
        """
        Decrypt CryptoJS.AES encrypted string.
        CryptoJS uses OpenSSL-compatible format: "Salted__" + 8 bytes salt + encrypted data
        """
        if not ciphertext:
            return ""
        
        try:
            # Decode base64
            encrypted = base64.b64decode(ciphertext)
            
            # Check for "Salted__" prefix (OpenSSL format)
            if encrypted[:8] == b'Salted__':
                # Extract salt (next 8 bytes)
                salt = encrypted[8:16]
                ciphertext_bytes = encrypted[16:]
                
                # Derive key and IV using OpenSSL's EVP_BytesToKey equivalent
                def derive_key_and_iv(password: bytes, salt: bytes, key_length: int = 32, iv_length: int = 16):
                    """
                    Mimics OpenSSL's EVP_BytesToKey function used by CryptoJS
                    """
                    d = d_i = b''
                    while len(d) < key_length + iv_length:
                        d_i = hashlib.md5(d_i + password + salt).digest()
                        d += d_i
                    return d[:key_length], d[key_length:key_length + iv_length]
                
                key, iv = derive_key_and_iv(ENCRYPTION_KEY.encode(), salt)
                
                # Decrypt
                cipher = AES.new(key, AES.MODE_CBC, iv)
                decrypted = unpad(cipher.decrypt(ciphertext_bytes), AES.block_size)
                
                return decrypted.decode('utf-8')
            else:
                # Not in OpenSSL format, might be plain AES
                print("⚠️ Ciphertext not in OpenSSL format")
                return ""
            
        except Exception as e:
            print(f"❌ AES Decryption failed: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    @staticmethod
    def encrypt_aes(plaintext: str) -> str:
        """
        Encrypt string to CryptoJS.AES compatible format.
        """
        if not plaintext:
            return ""
        
        try:
            # Generate random salt
            salt = os.urandom(8)
            
            # Derive key and IV
            def derive_key_and_iv(password: bytes, salt: bytes, key_length: int = 32, iv_length: int = 16):
                d = d_i = b''
                while len(d) < key_length + iv_length:
                    d_i = hashlib.md5(d_i + password + salt).digest()
                    d += d_i
                return d[:key_length], d[key_length:key_length + iv_length]
            
            key, iv = derive_key_and_iv(ENCRYPTION_KEY.encode(), salt)
            
            # Encrypt
            from Crypto.Util.Padding import pad
            cipher = AES.new(key, AES.MODE_CBC, iv)
            encrypted = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
            
            # Combine in OpenSSL format: "Salted__" + salt + encrypted
            result = b'Salted__' + salt + encrypted
            
            # Encode to base64
            return base64.b64encode(result).decode('utf-8')
            
        except Exception as e:
            print(f"❌ AES Encryption failed: {e}")
            import traceback
            traceback.print_exc()
            return ""