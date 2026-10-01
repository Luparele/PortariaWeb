import os
import requests
from dotenv import load_dotenv

def reload_pythonanywhere():
    # Carrega as variáveis do .env
    load_dotenv()
    
    username = os.getenv('PYTHONANYWHERE_USERNAME')
    token = os.getenv('PYTHONANYWHERE_TOKEN')
    
    if not username or not token:
        print("❌ Erro: PYTHONANYWHERE_USERNAME ou PYTHONANYWHERE_TOKEN não encontrados no .env!")
        return

    domain_name = f"{username}.pythonanywhere.com"
    
    print(f"🔄 Solicitando reload para {domain_name}...")
    
    url = f"https://www.pythonanywhere.com/api/v0/user/{username}/webapps/{domain_name}/reload/"
    
    response = requests.post(
        url,
        headers={'Authorization': f'Token {token}'}
    )
    
    if response.status_code == 200:
        print(f"✅ Sucesso! O servidor em {domain_name} foi reiniciado e as alterações já estão no ar.")
    else:
        print(f"❌ Erro ao recarregar o servidor. Código: {response.status_code}")
        print(response.content.decode())

if __name__ == "__main__":
    reload_pythonanywhere()
