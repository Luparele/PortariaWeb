import os
from django.core.files.storage import Storage
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from django.conf import settings
from django.utils.deconstruct import deconstructible

@deconstructible
class CustomGoogleDriveStorage(Storage):
    def __init__(self):
        self.folder_id = getattr(settings, 'GOOGLE_DRIVE_STORAGE_MEDIA_ROOT', None)
        self.credentials_file = getattr(settings, 'GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE', None)
        
        # Carrega as credenciais
        token_path = os.path.join(settings.BASE_DIR, 'token.json')
        if os.path.exists(token_path):
            from google.oauth2.credentials import Credentials as UserCredentials
            credentials = UserCredentials.from_authorized_user_file(
                token_path, scopes=['https://www.googleapis.com/auth/drive.file']
            )
        else:
            credentials = Credentials.from_service_account_file(
                self.credentials_file, scopes=['https://www.googleapis.com/auth/drive']
            )
        
        # Se estiver rodando no PythonAnywhere gratuito, precisamos forçar o proxy
        import httplib2
        import google_auth_httplib2

        try:
            import socks
            has_socks = True
        except ImportError:
            has_socks = False

        proxy_url = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
        if proxy_url and has_socks:
            proxy_info = httplib2.ProxyInfo(
                proxy_type=socks.PROXY_TYPE_HTTP,
                proxy_host='proxy.server',
                proxy_port=3128
            )
            http = httplib2.Http(proxy_info=proxy_info)
        else:
            http = httplib2.Http()

        authed_http = google_auth_httplib2.AuthorizedHttp(credentials, http=http)

        # Usa o discovery estático (embutido na biblioteca) para evitar requisições extras
        # e falhas de rede no PythonAnywhere
        self.service = build('drive', 'v3', http=authed_http, static_discovery=True)

    def _save(self, name, content):
        """Salva o arquivo diretamente pelo ID da pasta"""
        file_metadata = {
            'name': os.path.basename(name),
            'parents': [self.folder_id]
        }
        
        # O Django passa o arquivo através de content.file
        media = MediaIoBaseUpload(content.file, mimetype='application/octet-stream', resumable=False)
        
        # Faz o upload (uma única requisição, muito mais rápido)
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')

        # Concede permissão pública de leitura para que as tags <img> funcionem no HTML
        try:
            self.service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
        except Exception as e:
            print(f"Erro ao dar permissão pública na foto: {e}")

        # Retorna o ID do arquivo. O Django salvará esse ID no banco de dados (no ImageField).
        return file_id

    def url(self, name):
        """Retorna o link direto da imagem baseado no ID que foi salvo no banco"""
        # O Google Drive bloqueia iframes/img tags de uc?id em alguns navegadores novos.
        # A forma recomendada de embutir imagens publicas do drive agora é pelo endpoint de thumbnail.
        return f'https://drive.google.com/thumbnail?id={name}&sz=w1000'

    def delete(self, name):
        """Deleta a imagem do Google Drive"""
        try:
            self.service.files().delete(fileId=name).execute()
        except Exception:
            pass

    def exists(self, name):
        # Como o Django sempre gera UUID para os checklists, nunca haverá colisão.
        return False
        
    def size(self, name):
        return 0

def process_base64_signature(base64_str, filename_prefix="assinatura"):
    """
    Recebe uma string base64 de imagem, decodifica, faz o upload para
    uma subpasta 'Assinaturas' no Google Drive e retorna o link de visualização.
    """
    if not base64_str or not base64_str.startswith('data:image/'):
        return base64_str

    import base64
    import re
    import uuid
    from io import BytesIO
    from googleapiclient.http import MediaIoBaseUpload

    try:
        storage = CustomGoogleDriveStorage()
        service = storage.service
        parent_id = storage.folder_id
        
        # Procura se a pasta 'Assinaturas' já existe
        query = f"name='Assinaturas' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])
        
        if files:
            assinaturas_folder_id = files[0].get('id')
        else:
            folder_metadata = {
                'name': 'Assinaturas',
                'parents': [parent_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            assinaturas_folder_id = folder.get('id')

        # Extrai os dados base64
        match = re.match(r'data:image/(?P<format>jpeg|png|gif|webp);base64,(?P<data>.*)', base64_str)
        if match:
            ext = match.group('format')
            b64_data = match.group('data')
            image_data = base64.b64decode(b64_data)
            f = BytesIO(image_data)
            
            file_name = f"{filename_prefix}_{uuid.uuid4().hex[:8]}.{ext}"
            
            # Upload para o Google Drive
            file_metadata = {
                'name': file_name,
                'parents': [assinaturas_folder_id]
            }
            media = MediaIoBaseUpload(f, mimetype=f'image/{ext}', resumable=False)
            
            uploaded_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = uploaded_file.get('id')
            
            # Torna público
            service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            
            # Retorna o link encurtado
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
            
    except Exception as e:
        print(f"Erro ao salvar assinatura automática no Drive: {e}")
        
    return base64_str
