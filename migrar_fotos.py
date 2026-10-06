import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from checklists.models import ChecklistPhoto
from django.core.files import File
from django.conf import settings

def migrar_fotos():
    photos = ChecklistPhoto.objects.all()
    print(f"Encontradas {photos.count()} fotos no total.")
    
    migrados = 0
    erros = 0
    
    for photo in photos:
        # IDs do Google Drive normalmente não tem barras nem pontos de extensão
        if 'checklists/' in photo.file.name or '.' in photo.file.name:
            local_path = os.path.join(settings.BASE_DIR, 'media', photo.file.name)
            
            if os.path.exists(local_path):
                print(f"\nMigrando: {photo.file.name}...")
                try:
                    with open(local_path, 'rb') as f:
                        django_file = File(f)
                        # O Django vai chamar o _save do GDrive, fazer o upload e atualizar o ID
                        photo.file.save(photo.file.name, django_file)
                    
                    print(f"Sucesso! Novo ID do GDrive: {photo.file.name}")
                    migrados += 1
                    
                    # Apaga o arquivo físico do PythonAnywhere para liberar espaço
                    os.remove(local_path)
                except Exception as e:
                    print(f"Erro ao migrar {photo.file.name}: {e}")
                    erros += 1
            else:
                print(f"Arquivo não encontrado no disco (ignorando): {local_path}")
        else:
            # Já é um ID do GDrive
            pass
            
    print(f"\n--- MIGRAÇÃO CONCLUÍDA ---")
    print(f"Fotos migradas com sucesso e apagadas do disco local: {migrados}")
    print(f"Erros: {erros}")

if __name__ == '__main__':
    migrar_fotos()
