import os
import django
from datetime import timedelta

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') # Ajuste se o nome do projeto principal for diferente
django.setup()

from checklists.models import Checklist, MaintenanceTruck, MaintenanceTrailer, ChecklistForklift

def remove_duplicates(model_class, identify_fields):
    print(f"--- Verificando duplicidades em {model_class.__name__} ---")
    items = model_class.objects.all().order_by('data_criacao')
    
    deleted_count = 0
    previous_item = None
    
    for item in items:
        if previous_item:
            # Verifica se os campos que identificam a duplicidade são iguais
            is_duplicate = True
            for field in identify_fields:
                if getattr(item, field) != getattr(previous_item, field):
                    is_duplicate = False
                    break
            
            # Verifica se a diferença de tempo é menor que 2 minutos
            if is_duplicate:
                time_diff = item.data_criacao - previous_item.data_criacao
                if time_diff <= timedelta(minutes=2):
                    print(f"Duplicidade encontrada! Deletando ID: {item.id} (Original ID: {previous_item.id}) | Tempo: {item.data_criacao}")
                    item.delete()
                    deleted_count += 1
                    # Não atualiza o previous_item para que possamos deletar a 3ª, 4ª duplicidade se houver
                    continue 
                    
        previous_item = item

    print(f"Total de duplicidades removidas em {model_class.__name__}: {deleted_count}\n")

if __name__ == '__main__':
    print("Iniciando varredura de duplicidades...")
    
    # 1. Checklist Portaria
    remove_duplicates(Checklist, ['placa_cavalo_id', 'nome_motorista_id', 'porteiro_id'])
    
    # 2. Manutenção Caminhão
    remove_duplicates(MaintenanceTruck, ['veiculo_id', 'motorista_id', 'responsavel_id'])
    
    # 3. Manutenção Carreta
    remove_duplicates(MaintenanceTrailer, ['veiculo_id', 'motorista_id', 'responsavel_id'])
    
    # 4. Empilhadeiras
    remove_duplicates(ChecklistForklift, ['tipo_equipamento', 'operador_id', 'responsavel_id'])
    
    print("Varredura e limpeza concluídas com sucesso!")
