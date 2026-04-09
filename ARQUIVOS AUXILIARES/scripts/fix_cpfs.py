import os
import sys
import django

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from checklists.models import Profile
from django.contrib.auth.models import User

# Ensure all users have a profile
for user in User.objects.all():
    profile, created = Profile.objects.get_or_create(user=user)
    if not profile.cpf:
        profile.cpf = '000.000.000-00'
        profile.save()
        print(f'Updated CPF for {user.username}')
    else:
        print(f'User {user.username} already has CPF: {profile.cpf}')
