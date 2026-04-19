# Plano de Integração: WhatsApp Gateway para PortariaWeb

Este documento detalha a estratégia técnica para integrar notificações automáticas via WhatsApp no projeto **PortariaWeb**, utilizando uma arquitetura de fila de mensagens para garantir estabilidade e baixo custo.

## 1. Tecnologias de Referência
Para esta integração, foram analisadas e selecionadas as seguintes tecnologias:

*   **Agente de Comunicação:** [whatsapp-mcp](https://github.com/lharries/whatsapp-mcp)
    *   *Por que:* Utiliza o protocolo MCP (Model Context Protocol) e a biblioteca `whatsmeow` (Go), que é mais estável e leve para rodar em servidores como o PythonAnywhere.
*   **Framework Web:** Django (Base do PortariaWeb).
*   **Hospedagem:** PythonAnywhere (Plano Pago/Hacker).
    *   *Necessidade:* O plano pago permite conexões de socket irrestritas e a execução de tarefas "sempre ativas" (Always-on Tasks).

## 2. Arquitetura de Fila de Mensagens
Em vez de tentar uma conexão direta via HTTP (POST) entre o site e o bot de WhatsApp (o que é bloqueado pela rede interna do PythonAnywhere), utilizaremos o banco de dados como ponte.

### Fluxo de Funcionamento:
1.  **Trigger (Django):** Quando um checklist é salvo ou um status muda, o Django insere um registro na tabela `NotificacaoWhatsApp`.
2.  **Monitoramento (Agente):** Um script independente (Always-on Task) monitora essa tabela a cada 2 segundos.
3.  **Processamento:**
    *   O agente identifica uma nova mensagem.
    *   Envia para o JID (ID do grupo) correspondente via `whatsapp-mcp`.
    *   **Confirmação e Exclusão:** Assim que o WhatsApp confirma o recebimento pelo servidor, o registro é **deletado** do banco de dados.

### Vantagens desta escolha:
*   **Resiliência:** Se o bot cair ou a internet oscilar, as mensagens ficam seguras no banco de dados e são enviadas assim que a conexão volta.
*   **Performance:** Mantém o banco de dados limpo e leve, processando apenas o que é estritamente necessário.
*   **Desacoplamento:** O site não "trava" esperando o WhatsApp responder; o envio acontece de forma assíncrona.

## 3. Estratégia de Grupos e Risco de Banimento
Para minimizar o risco de banimento por parte da Meta (WhatsApp):
*   **Uso de Grupos:** As notificações serão enviadas para grupos específicos (Entrada/Saída, Manutenção, Agendamento).
*   **Vantagem:** O envio para grupos onde o bot é membro possui um risco de bloqueio significativamente menor do que o envio de mensagens privadas para múltiplos números.

## 4. Estimativa de Custos
*   **Infraestrutura:** ~$5.00/mês (Plano Hacker PythonAnywhere).
*   **Mensagens:** Isento de taxas por mensagem (utilizando API não oficial via socket).
*   **Comparativo:** Economia de aproximadamente R$ 480,00/mês em relação à API Oficial para um volume de 100 mensagens/dia.

---
*Documento gerado para o projeto PortariaWeb - 2026.*
