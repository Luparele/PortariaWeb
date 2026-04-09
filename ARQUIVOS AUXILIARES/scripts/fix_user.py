import django
import os
import sys

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from checklists.models import Profile

print("--- INICIANDO REPARO DE USUÁRIO ---")

# Procura admin insensível a maiúsculas
u = User.objects.filter(username__iexact='admin').first()
if u:
    print(f"Usuário encontrado: {u.username}")
    if u.username != 'ADMIN':
        u.username = 'ADMIN'
        u.save()
        print("Nome de usuário alterado para ADMIN")
    
    # Garante que o Perfil existe e é de ADMIN
    profile, created = Profile.objects.get_or_create(user=u)
    profile.role = 'ADMIN'
    profile.save()
    print(f"Perfil verificado para {u.username}. Role: {profile.role}")
    
    # Reset da senha para admin (temporário para teste)
    u.set_password('admin')
    u.save()
    print("Senha resetada para 'admin' para permitir teste de acesso.")
else:
    print("ERRO: Usuário 'admin' ou 'ADMIN' não encontrado!")

print("--- REPARO CONCLUÍDO ---")
