@echo off
title Sistema Check-up & Manutenção - Inicializador
mode con: cols=80 lines=25
cls

echo ============================================================
echo           SISTEMA CHECK-UP & MANUTENÇÃO - GERENCIAMENTO
echo ============================================================
echo.
echo [1/3] Liberando portas 8000 e 8001...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul

echo [2/3] Verificando Ambiente Virtual...
if not exist venv (
    echo [ERRO] Pasta 'venv' nao encontrada! 
    echo Certifique-se de que o ambiente virtual foi criado corretamente.
    pause
    exit
)

echo [3/3] Iniciando Servidor Django na porta 8000...
start "SERVIDOR - Checkup" cmd /k "venv\Scripts\activate && python manage.py runserver 8000"

:: Aguardar o servidor subir antes de abrir o navegador
timeout /t 3 /nobreak > nul

echo.
echo [!] Abrindo o Navegador em: http://127.0.0.1:8000
start http://127.0.0.1:8000

echo.
echo ============================================================
echo           SISTEMA INICIADO COM SUCESSO!
echo ============================================================
echo.
echo - Acesso Principal: http://127.0.0.1:8000
echo - Painel Admin:     http://127.0.0.1:8000/admin/
echo.
echo Mantenha a janela do servidor aberta para o sistema funcionar.
echo Pressione qualquer tecla para fechar este guia.
pause > nul

