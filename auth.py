"""Shared-password access. Set DASHBOARD_PASSWORD in server environment."""
import os,time,hmac,hashlib,secrets
from http.cookies import SimpleCookie
PASSWORD=os.environ.get('DASHBOARD_PASSWORD','Boost2026')
SECRET=os.environ.get('SESSION_SECRET') or secrets.token_hex(32)
TTL=8*60*60

def valid_cookie(headers):
 if not PASSWORD:return False
 try:
  c=SimpleCookie();c.load(headers.get('Cookie',''));value=c['dashboard_session'].value
  stamp,nonce,sig=value.split('.')
  base=stamp+'.'+nonce
  return 0<=time.time()-int(stamp)<TTL and hmac.compare_digest(sig,hmac.new(SECRET.encode(),base.encode(),hashlib.sha256).hexdigest())
 except Exception:return False

def cookie():
 base=str(int(time.time()))+'.'+secrets.token_hex(16)
 token=base+'.'+hmac.new(SECRET.encode(),base.encode(),hashlib.sha256).hexdigest()
 secure='; Secure' if os.environ.get('COOKIE_SECURE')=='1' else ''
 return f'dashboard_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={TTL}{secure}'
ATTEMPTS={}
def login(ip,password):
 now=time.time();history=[t for t in ATTEMPTS.get(ip,[]) if now-t<300];ATTEMPTS[ip]=history
 if len(history)>=10:return False
 if PASSWORD and hmac.compare_digest(str(password).encode(),PASSWORD.encode()):ATTEMPTS.pop(ip,None);return True
 history.append(now);return False
