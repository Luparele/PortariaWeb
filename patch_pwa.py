import os
import sys
import fileinput

def apply_patch():
    # Tenta encontrar o caminho do pywebpush no site-packages do venv
    try:
        import pywebpush
        target_file = os.path.abspath(pywebpush.__file__)
    except ImportError:
        print("Erro: Biblioteca pywebpush não encontrada no ambiente atual.")
        return

    if not os.path.exists(target_file):
        print(f"Erro: Arquivo não encontrado: {target_file}")
        return

    print(f"--- Aplicando patch de compatibilidade PWA em: {target_file} ---")
    
    content_changed = False
    # Lê o arquivo para verificar se já está patcheado
    with open(target_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    with open(target_file, 'w', encoding='utf-8') as f:
        for line in lines:
            if 'ec.SECP256R1, default_backend()' in line:
                new_line = line.replace('ec.SECP256R1, default_backend()', 'ec.SECP256R1(), default_backend()')
                f.write(new_line)
                content_changed = True
                print("Lógica detectada e corrigida: ec.SECP256R1 -> ec.SECP256R1()")
            else:
                f.write(line)
    
    if content_changed:
        print("✅ Patch aplicado com sucesso!")
    else:
        # Se não achou a string exata, verifica se já estava corrigido
        success = False
        with open(target_file, 'r', encoding='utf-8') as f:
            if 'ec.SECP256R1(), default_backend()' in f.read():
                print("ℹ️ O patch já estava aplicado ou a versão já é compatível.")
                success = True
        
        if not success:
            print("⚠️ Aviso: A string alvo não foi encontrada. Verifique a versão do pywebpush.")

if __name__ == "__main__":
    apply_patch()
