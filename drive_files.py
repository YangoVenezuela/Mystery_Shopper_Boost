"""Facturas y comprobantes en Google Drive. Credenciales solo en el servidor."""
import os,re,io,base64
from pathlib import Path
FOLDER='16L6tc-CiruDdhPhzKzne40lk_HDkJXMV'
MAX_FILE=10*1024*1024

def service():
 from google.oauth2.credentials import Credentials
 from google.oauth2 import service_account
 from googleapiclient.discovery import build
 candidates=[]
 for kind,var in [('service','GOOGLE_APPLICATION_CREDENTIALS'),('oauth','GOOGLE_TOKEN_FILE')]:
  if os.environ.get(var):candidates.append((kind,Path(os.environ[var])))
 if not candidates:
  directory=Path.home()/'.config/google-sheets/accounts';active=directory.parent/'active';slot=active.read_text().strip() if active.exists() else ''
  if directory.exists():candidates.extend(('oauth',p) for p in sorted(directory.glob('*.json'),key=lambda p:p.stem!=slot))
  for var in ['GOOGLE_SHEETS_TOKEN','GOOGLE_DOCS_TOKEN']:
   if os.environ.get(var) and Path(os.environ[var]).is_file():candidates.append(('oauth',Path(os.environ[var])))
 for kind,path in candidates:
  try:
   creds=service_account.Credentials.from_service_account_file(str(path),scopes=['https://www.googleapis.com/auth/drive']) if kind=='service' else Credentials.from_authorized_user_file(str(path))
   api=build('drive','v3',credentials=creds,cache_discovery=False)
   folder=api.files().get(fileId=FOLDER,fields='capabilities(canAddChildren)',supportsAllDrives=True).execute()
   if folder.get('capabilities',{}).get('canAddChildren'):return api
  except Exception:continue
 raise RuntimeError('La cuenta conectada necesita permiso Editor en la carpeta y autorización para Google Drive.')

def listing():
 api=service();files=[];token=None
 while True:
  result=api.files().list(q=f"'{FOLDER}' in parents and trashed=false and mimeType!='application/vnd.google-apps.folder'",fields='nextPageToken,files(id,name,webViewLink,createdTime,size,appProperties)',orderBy='createdTime desc',pageSize=100,pageToken=token,supportsAllDrives=True,includeItemsFromAllDrives=True).execute()
  for f in result.get('files',[]):
   props=f.get('appProperties',{});files.append({'id':f['id'],'name':f['name'],'url':f.get('webViewLink','https://drive.google.com/file/d/'+f['id']+'/view'),'month':props.get('month',''),'person':props.get('person',''),'kind':props.get('kind',''),'label':props.get('label',''),'created':f.get('createdTime','')})
  token=result.get('nextPageToken')
  if not token:break
 return {'files':files,'folder_url':'https://drive.google.com/drive/folders/'+FOLDER}

def clean(v,limit=80):return re.sub(r'[\x00-\x1f/\\<>:"|?*]','',str(v)).strip()[:limit]
def upload(payload):
 from googleapiclient.http import MediaIoBaseUpload
 month=str(payload.get('month',''));person=clean(payload.get('person',''));kind=payload.get('kind');label=clean(payload.get('label',''))
 if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',month):raise ValueError('Selecciona un mes válido.')
 if not person:raise ValueError('Indica el nombre de la persona.')
 if kind not in ['Factura','Comprobante de pago']:raise ValueError('Selecciona Factura o Comprobante de pago.')
 try:data=base64.b64decode(payload.get('data',''),validate=True)
 except Exception:raise ValueError('El archivo no es válido.')
 if not data or len(data)>MAX_FILE:raise ValueError('El archivo debe pesar como máximo 10 MB.')
 if data.startswith(b'%PDF-'):ext,mime='pdf','application/pdf'
 elif data.startswith(b'\x89PNG\r\n\x1a\n'):ext,mime='png','image/png'
 elif data.startswith(b'\xff\xd8\xff'):ext,mime='jpg','image/jpeg'
 else:raise ValueError('Solo se permiten archivos PDF, PNG o JPG.')
 name=f'{month} · {person} · {kind}'+(f' · {label}' if label else '')+'.'+ext
 api=service();f=api.files().create(body={'name':name,'parents':[FOLDER],'appProperties':{'month':month,'person':person,'kind':kind,'label':label}},media_body=MediaIoBaseUpload(io.BytesIO(data),mimetype=mime,resumable=False),fields='id,name,webViewLink',supportsAllDrives=True).execute()
 return {'id':f['id'],'name':f['name'],'url':f.get('webViewLink','https://drive.google.com/file/d/'+f['id']+'/view')}
