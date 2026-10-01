import os
import time
import requests
from dotenv import load_dotenv

load_dotenv('.env')
username = os.getenv('PYTHONANYWHERE_USERNAME')
token = os.getenv('PYTHONANYWHERE_TOKEN')

headers = {'Authorization': f'Token {token}'}
base_url = f'https://www.pythonanywhere.com/api/v0/user/{username}/consoles/'

print("Criando terminal remoto (Console)...")
resp = requests.post(base_url, headers=headers, json={"executable": "bash"})
if resp.status_code != 201:
    print("Erro ao criar console:", resp.text)
    exit(1)

console_id = resp.json()['id']
print(f"Console ID {console_id} criado.")

try:
    # Aguarda o console iniciar
    time.sleep(3)
    
    # Envia o comando
    print("Enviando comando 'du -sh ~/PortariaWeb'...")
    cmd_url = f"{base_url}{console_id}/send_input/"
    requests.post(cmd_url, headers=headers, json={"input": "du -sh ~/PortariaWeb\n"})
    
    # Aguarda o comando terminar e pega o output
    out_url = f"{base_url}{console_id}/get_latest_output/"
    output = ""
    for _ in range(5):
        time.sleep(2)
        out_resp = requests.get(out_url, headers=headers)
        output = out_resp.json().get('output', '')
        if 'PortariaWeb' in output or 'du' in output:
            break
            
    print("\n--- RESULTADO ---")
    print(output)
    print("-----------------\n")

finally:
    # Sempre deleta o console no final para não acumular
    print("Deletando o terminal...")
    requests.delete(f"{base_url}{console_id}/", headers=headers)
    print("Limpeza concluída.")
