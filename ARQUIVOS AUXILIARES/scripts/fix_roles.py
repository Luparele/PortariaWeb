import os
import sys
import django

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from checklists.models import Profile

def fix_roles():
    profiles = Profile.objects.filter(role='PORTEIRO')
    count = profiles.count()
    profiles.update(role='CONTROLADOR')
    print(f"Atualizados {count} perfis de PORTEIRO para CONTROLADOR.")

if __name__ == '__main__':
    fix_roles()
