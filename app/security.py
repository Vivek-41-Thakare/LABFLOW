import hashlib,hmac,secrets
from datetime import datetime,timedelta
from app.config import settings
def digest(v): return hmac.new(settings.secret_key.encode(),v.encode(),hashlib.sha256).hexdigest()
def otp(): return f"{secrets.randbelow(1000000):06d}"
def expires(minutes): return datetime.utcnow()+timedelta(minutes=minutes)
def token(): return secrets.token_urlsafe(32)
