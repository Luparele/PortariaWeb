import os
import django
import base64
import re
import io
from io import BytesIO

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from checklists.models import Checklist
from core.gdrive_storage import CustomGoogleDriveStorage
from googleapiclient.http import MediaIoBaseUpload

def get_or_create_subfolder(service, parent_id, folder_name):
    # Procura se a pasta já existe
    query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])
    
    if files:
        return files[0].get('id')
    
    # Se não existir, cria a pasta
    folder_metadata = {
        'name': folder_name,
        'parents': [parent_id],
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')

def migrar_assinaturas():
    print("Iniciando migração de assinaturas (Base64 para Google Drive)...")
    
    # Instancia o storage para aproveitar a conexão já configurada
    storage = CustomGoogleDriveStorage()
    service = storage.service
    parent_folder_id = storage.folder_id
    
    # Cria a subpasta "Assinaturas" no Drive
    assinaturas_folder_id = get_or_create_subfolder(service, parent_folder_id, "Assinaturas")
    print(f"Pasta de assinaturas pronta (ID: {assinaturas_folder_id})")
    
    checklists = Checklist.objects.all()
    print(f"Total de checklists a verificar: {checklists.count()}")
    
    campos_assinatura = [
        'visto_responsavel_saida',
        'visto_motorista_saida',
        'visto_responsavel_devolucao',
        'visto_motorista_devolucao'
    ]
    
    migrados = 0
    
    for ck in checklists:
        alterado = False
        for campo in campos_assinatura:
            valor = getattr(ck, campo)
            
            # Se o valor for um texto Base64
            if valor and valor.startswith('data:image/'):
                print(f"Migrando assinatura {campo} do checklist {ck.id}...")
                
                # Extrai os dados base64 ignorando o cabeçalho "data:image/png;base64,"
                match = re.match(r'data:image/(?P<format>jpeg|png|gif|webp);base64,(?P<data>.*)', valor)
                if match:
                    ext = match.group('format')
                    b64_data = match.group('data')
                    
                    try:
                        image_data = base64.b64decode(b64_data)
                        f = BytesIO(image_data)
                        
                        file_name = f"assinatura_ck_{ck.id}_{campo}.{ext}"
                        
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
                        
                        # Substitui no banco o Base64 GIGANTE pelo link curtinho do Google Drive
                        novo_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
                        setattr(ck, campo, novo_url)
                        alterado = True
                        migrados += 1
                        
                    except Exception as e:
                        print(f"Erro ao processar checklist {ck.id}: {e}")
                        
        if alterado:
            ck.save()
            print(f"Checklist {ck.id} salvo no banco com sucesso.")
            
    print(f"\n--- MIGRAÇÃO CONCLUÍDA ---")
    print(f"Total de assinaturas movidas para o Drive: {migrados}")
    print("\nAVISO: O banco de dados SQLite vai continuar com 146MB mesmo após os textos serem deletados. Você precisa rodar o VACUUM para ele encolher (fazer download pro seu PC e rodar).")

if __name__ == '__main__':
    migrar_assinaturas()
