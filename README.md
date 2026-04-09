# PortariaWeb - Sistema de Gestão e Monitoramento Operacional

![Logo](static/img/logo.png)

O **PortariaWeb** é uma solução robusta e moderna desenvolvida para a **Intalog Logistica Transportes Ltda**, focada na digitalização de processos de portaria, manutenção de frota e monitoramento de equipamentos pesados. O sistema substitui formulários em papel por uma interface digital ágil, segura e capaz de gerar dados analíticos em tempo real.

---

## 🎨 UI & UX (Interface e Experiência do Usuário)

O projeto foi concebido com foco na **eficiência operacional** e no uso em campo.

- **Design Premium & Minimalista**: Utiliza uma estética moderna com elementos de *glassmorphism*, sombras suaves e uma paleta de cores harmoniosa que facilita a leitura sob diferentes condições de iluminação.
- **Mobile-First & Responsivo**: Prioriza a utilização em tablets e smartphones, permitindo que controladores e mecânicos realizem inspeções diretamente ao lado dos veículos.
- **Experiência PWA (Progressive Web App)**: O sistema é instalável como um aplicativo nativo e utiliza *Service Workers* para garantir uma navegação fluida.
- **Assinatura Digital**: Implementação de captura de assinaturas diretamente na tela, garantindo a autenticidade das inspeções sem necessidade de papel.
- **Feedback Visual Instantâneo**: Indicadores de anomalias (vermelho/verde) e cronômetros de execução em tempo real orientam o usuário durante o processo.

---

## 🛠️ Tech Stack (Tecnologias Aplicadas)

### Backend
- **Python 3 / Django**: Framework principal para lógica de negócio, segurança e gestão de banco de dados.
- **Django Templates**: Motor de renderização para páginas dinâmicas de alto desempenho.

### Frontend
- **HTML5 & Vanilla CSS**: Estrutura e estilização customizada focada em performance.
- **JavaScript (ES6+)**: Lógica de interatividade, captura de assinaturas e gerenciamento de PWA.
- **Bootstrap 5**: Framework base para responsividade e componentes UI consistentes.

### Banco de Dados & Serviços
- **SQLite3**: Banco de dados padrão para desenvolvimento e operações locais ágeis.
- **Email & WhatsApp Integration**: Disparo automatizado de alertas para gestores quando anomalias são detectadas.

---

## 🚀 Funcionalidades Principais

1.  **Checklist de Portaria**:
    *   Inspeção completa de entrada e saída (Elétrica, Mecânica, Rodas/Pneus).
    *   Vínculo dinâmico entre Cavalo Mecânico e Carretas (Bitrem/Prancha).
    *   Registro de tempos de execução para auditoria de produtividade.

2.  **Módulo de Manutenção Especializada**:
    *   **Caminhão (29 itens)**: Verificação rigorosa de sistemas críticos.
    *   **Carreta (31 itens)**: Foco em estrutura lateral, pneus e sistema pneumático.
    *   **Empilhadeiras**: Checklists específicos para modelos MILA, ASA DELTA e HYSTER 7 TON.

3.  **Gestão de Anomalias (NC)**:
    *   Identificação automática de não-conformidades.
    *   Fluxo de resolução com registro de responsável e data de correção.

4.  **Agenda de Manutenção**:
    *   Cronograma de veículos parados com previsão de liberação e histórico de status.

5.  **Dashboard Administrativo**:
    *   Visão consolidada de métricas operacionais, heatmap de anomalias e estatísticas de uso.

---

## ⚖️ Direitos e Licenciamento

- **Desenvolvimento e Propriedade Intelectual**: [Eduardo Luparele Coelho](https://github.com/Luparele).
- **Direitos de Uso e Distribuição**: **Intalog Logistica Transportes Ltda** (CNPJ - 13.725.103/0001-60).

*Este software é de uso restrito e protegido por direitos autorais.*

---

## 🔧 Instalação e Execução

1.  Clone o repositório:
    ```bash
    git clone https://github.com/Luparele/PortariaWeb.git
    ```
2.  Crie e ative o ambiente virtual:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
3.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
4.  Inicie o servidor:
    ```bash
    python manage.py runserver
    ```
