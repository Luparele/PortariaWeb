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
                token_path, scopes=['https://www.googleapis.com/auth/drive']
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
        except Exception:
            pass

        # Retorna o ID do arquivo. O Django salvará esse ID no banco de dados (no ImageField).
        return file_id

    def url(self, name):
        """Retorna o link direto da imagem baseado no ID que foi salvo no banco"""
        # Como o _save retornou o ID, a variável 'name' aqui será na verdade o file_id do Google Drive!
        return f'https://drive.google.com/uc?id={name}'

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
