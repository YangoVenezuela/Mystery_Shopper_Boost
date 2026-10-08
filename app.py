"""Dashboard local de solo lectura para Questions. No modifica Google Sheets."""
import os,json,re,unicodedata,argparse
import auth
from pathlib import Path
from datetime import datetime,timedelta
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse

SHEET_ID='1RgmSfh7CrYIGdUGmKTznljJzl90f_Fw_5n2W9otxR_0'
ROOT=Path(__file__).parent
FIELDS=[('timestamp','Timestamp','Fecha y hora'),('email','Email Address','Correo'),('origin','Punto A','Origen'),('destination','Punto B','Destino'),('vehicle','Tipo de vehículo','Tarifa'),('yummy_image','Captura de pantalla del mismo viaje, pero en Yummy','Captura Yummy'),('ridery_image','Captura de pantalla del mismo viaje, pero en Ridery','Captura Ridery'),('yummy_price','Precio que te marca en Yummy','Yummy (USD)'),('ridery_price','Precio que te marca en Ridery','Ridery (USD)'),('yango_price','Precio que te marca en Yango','Yango (USD)'),('negotiated','¿El conductor te negoció el precio?','¿Negoció?'),('moment','¿En qué momento sucedió la renegociación?','Momento'),('channel','¿Por qué canal sucedió la renegociación?','Canal'),('evidence','Si tienes alguna evidencia física de la renegociación, súbela por favor.','Evidencia'),('final_usd','Precio final negociado con el conductor en $','Final (USD)'),('final_ves','Precio final negociado con el conductor en VES','Final (VES)'),('payment','Captura de pantalla del pago móvil al conductor','Comprobante'),('comments','Si tienes algún comentario o feedback sobre el uso de la plataforma, déjalo a continuación','Comentarios')]

def norm(s):
 return ' '.join(''.join(c for c in unicodedata.normalize('NFD',str(s)) if unicodedata.category(c)!='Mn').lower().split())
def date_value(v):
 if isinstance(v,(float,int)) and not isinstance(v,bool):
  try:return (datetime(1899,12,30)+timedelta(days=v)).isoformat(timespec='seconds')
  except (OverflowError,ValueError):return None
 if isinstance(v,str):
  try:return datetime.fromisoformat(v.strip()).isoformat(timespec='seconds')
  except ValueError:pass
  # The verified sheet locale is en_US. Prefer serial numbers from the API.
  for fmt in ('%m/%d/%Y %H:%M:%S','%m/%d/%Y %H:%M','%m/%d/%Y %I:%M:%S %p','%m/%d/%Y'):
   try:return datetime.strptime(v.strip(),fmt).isoformat(timespec='seconds')
   except ValueError:pass
 return None

def transform(values):
 if not values:return {'rows':[],'invalid_dates':0,'unknown_tariffs':0,'fields':[{'key':k,'label':l} for k,h,l in FIELDS]}
 headers={norm(h):i for i,h in enumerate(values[0])}
 missing=[h for k,h,l in FIELDS if norm(h) not in headers]
 if missing:raise ValueError('Faltan columnas: '+', '.join(missing))
 rows=[];invalid=unknown=0
 for line,row in enumerate(values[1:],2):
  if not any(str(c).strip() for c in row):continue
  obj={k:row[headers[norm(h)]] if headers[norm(h)]<len(row) else '' for k,h,l in FIELDS}
  dt=date_value(obj['timestamp'])
  if not dt:invalid+=1;continue
  vehicle={'moto':'Moto','economico':'Economy','economy':'Economy','comfort':'Confort','confort':'Confort'}.get(norm(obj['vehicle']))
  if not vehicle:unknown+=1;vehicle='Otra / sin tarifa'
  obj.update(timestamp=dt,date=dt[:10],vehicle=vehicle,source_row=line);rows.append(obj)
 rows.sort(key=lambda r:r['timestamp'],reverse=True)
 return {'rows':rows,'invalid_dates':invalid,'unknown_tariffs':unknown,'fields':[{'key':k,'label':l} for k,h,l in FIELDS]}

def fetch():
 from google.oauth2.credentials import Credentials
 from google.oauth2 import service_account
 from googleapiclient.discovery import build
 scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
 explicit=os.environ.get('GOOGLE_TOKEN_FILE')
 service=os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
 candidates=[]
 if service:candidates.append(('service',Path(service)))
 if explicit:candidates.append(('oauth',Path(explicit)))
 if not candidates:
  accountdir=Path.home()/'.config/google-sheets/accounts';activefile=accountdir.parent/'active'
  active=activefile.read_text().strip() if activefile.exists() else ''
  if accountdir.exists():
   paths=sorted(accountdir.glob('*.json'),key=lambda p:p.stem!=active)
   candidates.extend(('oauth',p) for p in paths)
  for var in ('GOOGLE_SHEETS_TOKEN','GOOGLE_DOCS_TOKEN'):
   p=os.environ.get(var)
   if p and Path(p).is_file():candidates.append(('oauth',Path(p)))
 if not candidates:raise RuntimeError('Configura GOOGLE_TOKEN_FILE o GOOGLE_APPLICATION_CREDENTIALS. Consulta README.md.')
 statuses=[]
 for kind,path in candidates:
  try:
   creds=service_account.Credentials.from_service_account_file(str(path),scopes=scopes) if kind=='service' else Credentials.from_authorized_user_file(str(path))
   api=build('sheets','v4',credentials=creds,cache_discovery=False)
   meta=api.spreadsheets().get(spreadsheetId=SHEET_ID,fields='properties(locale,timeZone)').execute()['properties']
   data=api.spreadsheets().values().get(spreadsheetId=SHEET_ID,range="'Questions'!A:AZ",valueRenderOption='UNFORMATTED_VALUE',dateTimeRenderOption='SERIAL_NUMBER').execute()
   result=transform(data.get('values',[]));result.update(timezone=meta.get('timeZone'),updated_at=datetime.now().isoformat(timespec='seconds'));return result
  except ValueError:raise
  except Exception as e:
   # Never include token values, credential paths, emails or raw Google errors.
   statuses.append(str(getattr(getattr(e,'resp',None),'status','conexión/autorización')))
 raise RuntimeError('No se pudo leer Questions. Revisa acceso a la hoja y conexión. Estados: '+', '.join(statuses))

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  path=urlparse(self.path).path
  origin=self.headers.get('Origin')
  allowed=os.environ.get('APP_ORIGIN') or 'http://'+self.headers.get('Host','')
  if origin and origin!=allowed:self.send_error(403);return
  if path=='/api/login':
   try:
    size=int(self.headers.get('Content-Length','0'));assert 0<size<=4096
    password=json.loads(self.rfile.read(size)).get('password','');ok=auth.login(self.client_address[0],password)
   except Exception:ok=False
   self.send_response(200 if ok else 401)
   if ok:self.send_header('Set-Cookie',auth.cookie())
   self.send_header('Cache-Control','no-store');self.end_headers();return
  if path=='/api/logout':
   self.send_response(200);self.send_header('Set-Cookie','dashboard_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0');self.end_headers();return
  if not auth.valid_cookie(self.headers):self.send_error(401);return
  if path!='/api/files':self.send_error(404);return
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size<=0 or size>15*1024*1024:raise ValueError('Archivo demasiado grande; máximo 10 MB.')
   from drive_files import upload
   payload=upload(json.loads(self.rfile.read(size)));status=201
  except Exception as e:payload={'error':str(e) if isinstance(e,(RuntimeError,ValueError)) else 'No se pudo guardar en Drive. Intenta de nuevo.'};status=400
  body=json.dumps(payload,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def do_GET(self):
  path=urlparse(self.path).path
  if path=='/login':
   body=(ROOT/'login.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body);return
  if path!='/yango_logo.png' and not auth.valid_cookie(self.headers):
   if path.startswith('/api/'):
    self.send_response(401);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b'{"error":"Debes iniciar sesion."}')
   else:self.send_response(302);self.send_header('Location','/login');self.end_headers()
   return
  if path=='/api/files':
   try:
    from drive_files import listing
    payload=listing();status=200
   except Exception as e:payload={'error':str(e) if isinstance(e,RuntimeError) else 'No se pudieron consultar los archivos de Drive.'};status=502
   body=json.dumps(payload,ensure_ascii=False).encode();mime='application/json; charset=utf-8'
  elif path=='/api/trips':
   try:payload=fetch();status=200
   except Exception as e:payload={'error':str(e) if isinstance(e,(ValueError,RuntimeError)) else 'No se pudo cargar la hoja.'};status=502
   body=json.dumps(payload,ensure_ascii=False).encode();mime='application/json; charset=utf-8'
  elif path in ('/','/index.html','/yango_logo.png'):
   file=ROOT/('index.html' if path in ('/','/index.html') else 'yango_logo.png');body=file.read_bytes();status=200;mime='image/png' if file.suffix=='.png' else 'text/html; charset=utf-8'
  else:self.send_error(404);return
  self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=int(os.environ.get('PORT','8765')));args=parser.parse_args()
 if not auth.PASSWORD:raise SystemExit('Configura DASHBOARD_PASSWORD antes de iniciar. Consulta README.md.')
 print(f'Abre http://127.0.0.1:{args.port} - Ctrl+C para detener.')
 ThreadingHTTPServer((os.environ.get('HOST','127.0.0.1'),args.port),Handler).serve_forever()
