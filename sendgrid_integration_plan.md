# Plano de Integração: Notificações de E-mail via SendGrid

Este documento descreve a estratégia para implementar notificações de e-mail no projeto **PortariaWeb**, superando as restrições técnicas do plano gratuito do PythonAnywhere.

## 1. O Problema: Restrições do PythonAnywhere Free
O plano gratuito do PythonAnywhere impede o envio de e-mails via protocolos padrão (SMTP) nas portas 25, 465 e 587. Isso impossibilita o uso direto de contas Gmail, Outlook ou servidores de hospedagem comuns.

## 2. A Solução: SendGrid Web API
Diferente do SMTP, o SendGrid oferece uma **Web API baseada em HTTP/HTTPS**. Como o domínio da API do SendGrid está na "lista branca" (whitelist) do PythonAnywhere, as requisições enviadas por este método são permitidas.

### Vantagens:
*   **Compatibilidade:** Funciona 100% no plano gratuito do PythonAnywhere.
*   **Custo Zero:** O plano gratuito do SendGrid permite até **100 e-mails por dia**, o que cobre a demanda estimada de 50 checklists diários.
*   **Rastreamento:** Permite saber se o e-mail foi entregue, aberto ou se houve erro.

## 3. Fluxo de Implementação

### Passo 1: Configuração no SendGrid
1.  Criar conta em [sendgrid.com](https://sendgrid.com).
2.  Realizar o **Sender Authentication** (verificar seu e-mail ou domínio de envio).
3.  Gerar uma **API Key** com permissões de "Mail Send".

### Passo 2: Integração no Django
Instalar a biblioteca oficial:
```bash
pip install sendgrid
```

Adicionar as credenciais ao arquivo `settings.py` (ou variáveis de ambiente):
```python
SENDGRID_API_KEY = 'sua_api_key_aqui'
DEFAULT_FROM_EMAIL = 'seu-email-verificado@dominio.com'
```

### Passo 3: Lógica de Envio
Criar uma função utilitária para disparar os alertas:
```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def enviar_email_alerta(assunto, conteudo, destinatario):
    message = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=destinatario,
        subject=assunto,
        plain_text_content=conteudo
    )
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        print(f"Erro SendGrid: {e}")
        return False
```

## 4. Integração com a Fila de Mensagens (Opcional)
Para máxima robustez, os e-mails podem seguir a mesma lógica do WhatsApp:
1.  Django salva o e-mail na tabela `FilaNotificacao`.
2.  O Agente (Task) processa a fila e tenta o envio via SendGrid.
3.  Em caso de sucesso, o registro é removido.

---
*Documento gerado para o projeto PortariaWeb - 2026.*
