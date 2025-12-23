# Automação de Reclassificação: Conta de Juros CC14

## Visão Geral do Projeto
A automação realiza a reclassificação contábil de juros da conta CC14, executando automaticamente no 3º dia útil de cada mês. O processo coleta dados via API, processa as informações conforme regras contábeis específicas, envia lançamentos para o sistema MegaIntegrador, armazena relatórios no SharePoint e notifica a equipe via Microsoft Teams.

**Departamentos envolvidos:** Contabilidade; Núcleo de Inteligência Artificial (GOS).

**Autor responsável:** Yasmim Augusto dos Santos - Núcleo de Excelência - GOS.

**Data de criação:** Dezembro/2025.

### Valor de Negócio
- **Redução de erros:** elimina processamento manual de reclassificações contábeis.
- **Aumento de eficiência:** execução automática mensal com validações integradas.
- **Conformidade/auditoria:** logging detalhado, telemetria em banco de dados e rastreabilidade completa.
- **Transparência:** notificações automáticas com resumo executivo e link para documentos.

## Principais Características Técnicas
- Configurabilidade via `.env` para ambientes de desenvolvimento e produção.
- Uso de pandas para processamento estruturado de dados contábeis.
- Robustez em chamadas de API com tratamento de erros e retry automático.
- Logging estruturado em `/logs` com identificador único de execução (run_id).
- Telemetria opcional em PostgreSQL (Supabase) para monitoramento e auditoria.
- Arquitetura orientada a objetos com separação clara de camadas (MVC).
- Modo DRY_RUN para testes sem impacto em produção.

## Arquitetura do Software
- **/config** – leitura de variáveis de ambiente (.env) e validação de chaves obrigatórias (settings.py).
- **/controllers** – lógica de orquestração em 9 etapas (reclassification_controller.py).
- **/services** – integrações externas:
  - APIs de reclassificação e lançamento contábil
  - Microsoft Graph/SharePoint para upload de relatórios
  - Microsoft Teams para notificações via webhook
  - PostgreSQL para telemetria de execução (opcional)
  - Logging estruturado com rotação de arquivos
- **/models** – regras de negócio e transformações:
  - Processamento de dados da API (reclassification_processor.py)
  - Montagem de estrutura WordData para MegaIntegrador (worddata_builder.py)
- **/utils** – funções auxiliares:
  - Cálculo de dias úteis e datas (business_calendar.py)
  - Configuração de logging (logger.py)
- **/tests** – testes unitários e de integração com dados de amostra.
- **/logs** – diretório onde são gravados os logs de cada execução.
- **/docs** – documentação complementar (process_overview.md, technical_details.md).
- **main.py** – ponto de entrada que inicializa o ambiente e dispara o controlador principal.

## Stack Tecnológico
- **Linguagem:** Python 3.10+
- **Principais bibliotecas:**
  - pandas (processamento de dados)
  - requests (chamadas HTTP)
  - python-dotenv (gerenciamento de variáveis de ambiente)
  - openpyxl (geração de planilhas Excel)
  - psycopg2-binary (conexão PostgreSQL - opcional)
  - logging (sistema de logs estruturado)
- **APIs externas:**
  - API de Reclassificação (coleta de dados)
  - MegaIntegrador (envio de lançamentos contábeis)
  - Microsoft Graph (upload para SharePoint)
  - Microsoft Teams Webhook (notificações)
  - Supabase PostgreSQL (telemetria - opcional)

## Regras de Execução
- **Agendamento:** Executa automaticamente no 3º dia útil de cada mês.
- **Período processado:** Mês anterior completo (data_inicial a data_final).
- **Modo forçado:** Variável `FORCAR_EXECUCAO=true` permite execução em qualquer data (para testes).
- **Modo simulação:** Variável `DRY_RUN=true` simula operações sem executar de verdade.

## Documentação Adicional
- **Visão funcional do processo:** docs/process_overview.md
- **Guia técnico completo:** docs/technical_details.md
- **Testes e validações:** tests/README.md