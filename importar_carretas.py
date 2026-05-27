import os
import sys
import django

# Configura o ambiente do Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from checklists.models import Veiculo

# Dados extraídos do arquivo Excel (carretas.xlsx)
DATA = [{"Categoria da Carreta": "CARRETA", "placa": "KVR-4J05", "marca/modelo": "SR/RODOFORT", "ano": 2011, "RENAVAN": 416911218}, {"Categoria da Carreta": "CARRETA", "placa": "KVC-3J35", "marca/modelo": "SR / LIBRELATO", "ano": 2009, "RENAVAN": 148222412}, {"Categoria da Carreta": "CARRETA", "placa": "LVD-6E03", "marca/modelo": "SR / RANDON", "ano": 2006, "RENAVAN": 881458007}, {"Categoria da Carreta": "CARRETA", "placa": "BYA-8C78", "marca/modelo": "SR / RANDON", "ano": 1994, "RENAVAN": 620730676}, {"Categoria da Carreta": "CARRETA", "placa": "KPC-7C35", "marca/modelo": "SR / RANDON", "ano": 1997, "RENAVAN": 686112814}, {"Categoria da Carreta": "CARRETA", "placa": "MAJ-8E31", "marca/modelo": "R / GUERRA", "ano": 1999, "RENAVAN": 712656944}, {"Categoria da Carreta": "CARRETA", "placa": "MPR-2B60", "marca/modelo": "SR/ FACCHINI", "ano": 2003, "RENAVAN": 817195858}, {"Categoria da Carreta": "CARRETA", "placa": "LPH-0B01", "marca/modelo": "SR/ FACCHINI", "ano": 2003, "RENAVAN": 817638032}, {"Categoria da Carreta": "CARRETA", "placa": "LQB-0B29", "marca/modelo": "SR/ FACCHINI", "ano": 2003, "RENAVAN": 817637656}, {"Categoria da Carreta": "CARRETA", "placa": "KZS-6A83", "marca/modelo": "SR/ FACCHINI", "ano": 2006, "RENAVAN": 893627984}, {"Categoria da Carreta": "CARRETA", "placa": "LVC-9D53", "marca/modelo": "SR/ FACCHINI", "ano": 2006, "RENAVAN": 886656974}, {"Categoria da Carreta": "CARRETA", "placa": "LQL-2D59", "marca/modelo": "SR/ FACCHINI", "ano": 2008, "RENAVAN": 965404480}, {"Categoria da Carreta": "CARRETA", "placa": "KNO-7E71", "marca/modelo": "SR/ FACCHINI", "ano": 2008, "RENAVAN": 968182542}, {"Categoria da Carreta": "CARRETA", "placa": "KVT-3D60", "marca/modelo": "SR/ FACCHINI", "ano": 2008, "RENAVAN": 110340582}, {"Categoria da Carreta": "CARRETA", "placa": "KNL-8G32", "marca/modelo": "SR/ FACCHINI", "ano": 2008, "RENAVAN": 959170669}, {"Categoria da Carreta": "CARRETA", "placa": "LPD-9C50", "marca/modelo": "SR/ FACCHINI", "ano": 2008, "RENAVAN": 963862197}, {"Categoria da Carreta": "CARRETA", "placa": "KOL-1G80", "marca/modelo": "SR/ FACCHINI", "ano": 2008, "RENAVAN": 963994611}, {"Categoria da Carreta": "CARRETA", "placa": "KVV-3A45", "marca/modelo": "SR/ FACCHINI", "ano": 2008, "RENAVAN": 979543967}, {"Categoria da Carreta": "CARRETA", "placa": "KVU-3A67", "marca/modelo": "SR/ FACCHINI", "ano": 2008, "RENAVAN": 979543444}, {"Categoria da Carreta": "CARRETA", "placa": "LTR-3E35", "marca/modelo": "SR/ FACCHINI", "ano": 2011, "RENAVAN": 323255655}, {"Categoria da Carreta": "CARRETA", "placa": "KWS-4C41", "marca/modelo": "SR/ FACCHINI", "ano": 2011, "RENAVAN": 323733522}, {"Categoria da Carreta": "CARRETA", "placa": "KRN-2G57", "marca/modelo": "SR/ FACCHINI", "ano": 2011, "RENAVAN": 323259545}, {"Categoria da Carreta": "CARRETA", "placa": "KWK-3G48", "marca/modelo": "SR/ FACCHINI", "ano": 2011, "RENAVAN": 336324448}, {"Categoria da Carreta": "CARRETA", "placa": "KVL-5E79", "marca/modelo": "SR/ FACCHINI", "ano": 2011, "RENAVAN": 336321660}, {"Categoria da Carreta": "CARRETA", "placa": "LQA-4E33", "marca/modelo": "SR/ FACCHINI", "ano": 2011, "RENAVAN": 377939030}, {"Categoria da Carreta": "CARRETA", "placa": "MSB-9A95", "marca/modelo": "SR/ NOMA", "ano": 2011, "RENAVAN": 758176597}, {"Categoria da Carreta": "CARRETA", "placa": "KOM-9231", "marca/modelo": "LIBRELATO", "ano": 2011, "RENAVAN": 353261327}, {"Categoria da Carreta": "CARRETA", "placa": "KOM-9280", "marca/modelo": "LIBRELATO", "ano": 2011, "RENAVAN": 353368270}, {"Categoria da Carreta": "CARRETA", "placa": "KOM-9C76", "marca/modelo": "LIBRELATO", "ano": 2011, "RENAVAN": 353358355}, {"Categoria da Carreta": "CARRETA", "placa": "KVL-7116", "marca/modelo": "LIBRELATO", "ano": 2011, "RENAVAN": 328889415}, {"Categoria da Carreta": "CARRETA", "placa": "KVP-1E72", "marca/modelo": "GUERRA", "ano": 2007, "RENAVAN": 935175059}, {"Categoria da Carreta": "CARRETA", "placa": "KWF-5194", "marca/modelo": "LIBRELATO", "ano": 2011, "RENAVAN": 353273155}, {"Categoria da Carreta": "CARRETA", "placa": "LPV-8J86", "marca/modelo": "LIBRELATO", "ano": 2011, "RENAVAN": 328890421}, {"Categoria da Carreta": "CARRETA", "placa": "KYV7819", "marca/modelo": "LIBRELATO", "ano": 2011, "RENAVAN": 328891223}, {"Categoria da Carreta": "BUGGY 20", "placa": "KYB-1355", "marca/modelo": "GUERRA", "ano": 2008, "RENAVAN": 977796116}, {"Categoria da Carreta": "BUGGY 20", "placa": "KPR-2F25", "marca/modelo": "LIBRELATO", "ano": 2010, "RENAVAN": 256319650}, {"Categoria da Carreta": "BUGGY 20", "placa": "LCP-0959", "marca/modelo": "FACCHINI", "ano": 2004, "RENAVAN": 834523329}, {"Categoria da Carreta": "BUGGY 20", "placa": "LLH-2506", "marca/modelo": "LIBRELATO", "ano": 2010, "RENAVAN": 253784018}, {"Categoria da Carreta": "BUGGY 20", "placa": "LQT-1G26", "marca/modelo": "SR/FACCHINI SRF ", "ano": 2006, "RENAVAN": 900764155}, {"Categoria da Carreta": "PRANCHA", "placa": "KWG-2818", "marca/modelo": "PRANCHA", "ano": 2008, "RENAVAN": 989881342}, {"Categoria da Carreta": "PRANCHA", "placa": "LQD-4328", "marca/modelo": "PRANCHA", "ano": 2012, "RENAVAN": 460345850}, {"Categoria da Carreta": "PRANCHA", "placa": "HCS-3G10", "marca/modelo": "PRANCHA", "ano": 1986, "RENAVAN": 243303270}, {"Categoria da Carreta": "PRANCHA", "placa": "LQD-4329", "marca/modelo": "PRANCHA", "ano": 2012, "RENAVAN": 460345575}, {"Categoria da Carreta": "SIDER", "placa": "KJA-6H13", "marca/modelo": "SIDER", "ano": 2006, "RENAVAN": 885628365}, {"Categoria da Carreta": "SIDER", "placa": "KJA-6H43", "marca/modelo": "SIDER", "ano": 2006, "RENAVAN": 885627636}, {"Categoria da Carreta": "BAÚ SECO", "placa": "LPN-5111", "marca/modelo": "SR/SAO PEDRO SRFB", "ano": 2005, "RENAVAN": 856218480}]

def run():
    print("Iniciando importação de carretas...")
    for item in DATA:
        cat_str = str(item.get("Categoria da Carreta", "")).strip()
        
        # Mapeamento para as choices do modelo
        if cat_str == "BUGGY 20":
            categoria = "BUGGY_20"
        elif cat_str == "BAÚ SECO":
            categoria = "BAU_SECO"
        elif cat_str == "CARRETA":
            categoria = "CARRETA"
        elif cat_str == "SIDER":
            categoria = "SIDER"
        elif cat_str == "PRANCHA":
            categoria = "PRANCHA"
        else:
            categoria = cat_str
            
        placa = str(item.get("placa", "")).strip().upper()
        # Algumas placas podem estar sem hífen, não há problema, mas caso precise:
        # placa = placa.replace("-", "") # se quiser padronizar sem hífen
        
        marca_modelo = str(item.get("marca/modelo", "")).strip()
        ano = str(item.get("ano", "")).strip()
        renavam = str(item.get("RENAVAN", "")).strip()
        
        # Trata formato '2011.0' caso pandas tenha convertido algo para float
        if ano.endswith('.0'):
            ano = ano[:-2]
        if renavam.endswith('.0'):
            renavam = renavam[:-2]
            
        try:
            veiculo, created = Veiculo.objects.get_or_create(
                placa=placa,
                defaults={
                    'tipo': 'CARRETA',
                    'marca_modelo': marca_modelo,
                    'ano': ano,
                    'renavam': renavam,
                    'categoria': categoria
                }
            )
            if created:
                print(f"✅ Criada: {placa} - {marca_modelo}")
            else:
                veiculo.tipo = 'CARRETA'
                veiculo.marca_modelo = marca_modelo
                veiculo.ano = ano
                veiculo.renavam = renavam
                veiculo.categoria = categoria
                veiculo.save()
                print(f"🔄 Atualizada: {placa} - {marca_modelo}")
        except Exception as e:
            print(f"❌ Erro ao salvar placa {placa}: {str(e)}")

    print("🚀 Importação concluída com sucesso!")

if __name__ == '__main__':
    run()
