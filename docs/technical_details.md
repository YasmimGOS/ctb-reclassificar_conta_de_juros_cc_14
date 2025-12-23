# Detalhes Técnicos: Automação Reclassificação Conta de Juros CC14

Este documento descreve a arquitetura técnica e os componentes principais da automação, servindo como referência para manutenção e futuras expansões.

---

## 1. Estrutura de Arquivos do Projeto

A estrutura do projeto foi organizada para separar claramente responsabilidades, facilitando testes e evolução.

```text
/ctb-reclassificar_conta_de_juros_cc_14
│
├── config/
│   ├── .env                              # Variáveis de ambiente (NÃO VERSIONAR)│   ├── __init__.py
│   └── settings.py                       # Carregamento e validação do .env
│
├── controllers/
│   ├── __init__.py
│   └── reclassification_controller.py    # Orquestração das 9 etapas
│
├── docs/
│   ├── README.md                         # Visão geral do projeto
│   ├── process_overview.md               # Visão funcional do processo
│   └── technical_details.md              # Este arquivo
│
├── logs/                                 # Logs de execução (gerados automaticamente)
│
├── models/
│   ├── __init__.py
│   ├── reclassification_processor.py     # Processamento e regras de negócio
│   └── worddata_builder.py               # Montagem de estrutura WordData
│
├── services/
│   ├── __init__.py
│   ├── accounting_api.py                 # API MegaIntegrador (lançamentos contábeis)
│   ├── db_service.py                     # Classe ExecutionLogger (PostgreSQL)
│   ├── execution_tracking.py             # Telemetria de execução (wrapper)
│   ├── reclassification_api.py           # API de Reclassificação (coleta dados)
│   ├── sharepoint_service.py             # Microsoft Graph/SharePoint
│   └── teams_notifier.py                 # Notificações via Teams webhook
│
├── tests/
│   ├── __init__.py
│   ├── test_data_sample.py               # Dados de amostra compartilhados
│   ├── test_excel_generation.py          # Teste de geração Excel
│   ├── test_worddata_structure.py        # Teste de estrutura WordData
│   ├── test_execution.py                 # Teste de execução completa
│   └── run_all_tests.py                  # Runner de todos os testes
│
├── utils/
│   ├── __init__.py
│   ├── business_calendar.py              # Cálculo de dias úteis e feriados
│   ├── excel_generator.py                # Gera Excel
│   ├── http_client.py                    # Cliente HTTP seguro com retry e timeout
│   ├── logger.py                         # Configuração de logging estruturado
│   ├── rate_limiter.py                   # Rate limiter usando algoritmo Token Bucket
│   ├── sanitizer.py                      # Sanitização de dados sensíveis para logs e notificações
│   └── sharepoint_discovery.py           # Utilitário para descobrir IDs do SharePoint dinamicamente.
├── .gitignore                            # Arquivos ignorados pelo Git
├── main.py                               # Ponto de entrada da aplicação              
└── requirements.txt                      # Dependências de produção
```

---

## 2. Descrição dos Componentes

### 📁 `config/`
Centraliza configurações e carregamento das variáveis de ambiente.

- **`.env`**: arquivo **obrigatório** (NÃO versionado) contendo as variáveis de execução.
- **`settings.py`**: carrega e valida o `.env`, expondo constantes.

**Variáveis obrigatórias:**
```python
# APIs Externas
API_RECLASSIFICACAO_URL
API_RECLASSIFICACAO_TOKEN
API_MEGAINTEGRADOR_URL
API_MEGAINTEGRADOR_TOKEN

# Microsoft Graph / SharePoint
TENANT_ID
CLIENT_ID
CLIENT_SECRET
GRAPH_DRIVE_ID
GRAPH_FOLDER_ID

# Teams Webhook
TEAMS_WEBHOOK_URL

# Telemetria (Opcional)
EXECUTION_DB_DSN

# Controle de Execução
FORCAR_EXECUCAO
DRY_RUN
TEST_SHAREPOINT_TEAMS
```

---

### 📁 `controllers/`
Responsável por orquestrar o fluxo principal da automação.

- **`reclassification_controller.py`**: expõe a função `run()` que:
  - **Etapa 1:** Verifica se hoje é o 3º dia útil (antes de iniciar telemetria)
  - **Etapa 2:** Calcula datas do mês anterior
  - **Etapa 3:** Chama API de reclassificação
  - **Etapa 4:** Processa dados (separa créditos/débitos, aplica regras)
  - **Etapa 5:** Monta WordData (estrutura JSON)
  - **Etapa 6:** Envia lançamentos contábeis
  - **Etapa 7:** Autentica Microsoft Graph
  - **Etapa 8:** Faz upload para SharePoint
  - **Etapa 9:** Notifica sucesso no Teams

Cada etapa é instrumentada com `StepLogger` (context manager) para registro automático de início/fim/status.

---

### 📁 `models/`
Define transformações e regras de negócio aplicadas aos dados.

#### **`reclassification_processor.py`**
- **Função principal:** `processar_reclassificacao(dados_api, data_inicial, data_final)`
- **Responsabilidades:**
  - Converter dados da API para DataFrame pandas
  - Adicionar colunas `DATA_INICIAL` e `DATA_FINAL`
  - Separar créditos (centros de custo que receberão juros)
  - Identificar débito (Diretoria Financeira - 11102001)
  - Remover Diretoria Operacional (12200001) dos créditos
  - Gerar DataFrame Excel com coluna `VALORDEBITO` calculada
- **Retornos:**
  - `df_creditos`: DataFrame de créditos (sem 12200001)
  - `diretoria_financeira_info`: dict com informações do débito
  - `df_completo`: DataFrame para Excel (créditos + débito)

#### **`worddata_builder.py`**
- **Função principal:** `montar_word_data(df_creditos, diretoria_financeira_info)`
- **Responsabilidades:**
  - Montar lista de itens de lançamento no formato WordData (JSON)
  - Cada item possui: `CENTROCUSTO`, `CONTADEBITO/CONTACREDITO`, `VALORDEBITO/VALORCREDITO`
  - Adicionar item de débito (Diretoria Financeira) ao final
  - Validar balanceamento: soma(créditos) = débito
- **Retorno:** lista de dicionários pronta para envio à API MegaIntegrador

---

### 📁 `services/`
Implementa comunicações externas e funcionalidades de suporte.

#### **`reclassification_api.py`**
- **Função:** `chamar_api_reclassificacao(data_inicial, data_final)`
- **Responsabilidade:** buscar dados de reclassificação via API externa
- **Tratamento de erros:** retry automático, logging detalhado, notificação no Teams se falhar

#### **`accounting_api.py`**
- **Função:** `chamar_api_lancamento_contabil(itens_lancamento, data_final)`
- **Responsabilidade:** enviar WordData para API MegaIntegrador
- **Modo DRY_RUN:** simula envio sem executar de verdade
- **Tratamento de erros:** valida resposta da API, notifica Teams se falhar

#### **`sharepoint_service.py`**
- **Funções:**
  - `get_graph_access_token()`: obtém token OAuth2 via client credentials
  - `upload_to_sharepoint(df, token)`: faz upload de Excel para SharePoint
- **Responsabilidades:**
  - Autenticação Microsoft Graph
  - Geração de Excel em memória (openpyxl)
  - Upload via Microsoft Graph API
  - Retorno de link público do arquivo
- **Modo TEST_SHAREPOINT_TEAMS:** desabilita upload em testes

#### **`teams_notifier.py`**
- **Funções:**
  - `notificar_sucesso(df_creditos, diretoria_financeira_info, link_arquivo)`: notificação de sucesso
  - `notificar_erro_api(mensagem_erro)`: notificação de erro
- **Responsabilidade:** enviar mensagens formatadas (Adaptive Cards) para Teams
- **Modo TEST_SHAREPOINT_TEAMS:** desabilita envio em testes

#### **`db_service.py`**
- **Classe:** `ExecutionLogger`
- **Responsabilidades:**
  - Pool de conexões PostgreSQL (psycopg2)
  - Registro de execuções na tabela `execution_runs`
  - Registro de etapas na tabela `execution_steps`
  - Atualização de progresso (0-100%)
- **Métodos principais:**
  - `start_run()`: inicia execução
  - `end_run(status, error_message)`: finaliza execução
  - `start_step(step_name, step_order)`: inicia etapa
  - `end_step(step_name, status, error_message)`: finaliza etapa
  - `update_progress(progress)`: atualiza percentual

#### **`execution_tracking.py`**
- **Responsabilidade:** wrapper sobre `ExecutionLogger` que facilita uso
- **Funções principais:**
  - `start_run(process_name)`: retorna (run_id, started_at)
  - `end_run_ok(run_id, started_at)`
  - `end_run_failed(run_id, started_at, error_message)`
  - `end_run_cancelled(run_id, started_at, reason)`
  - `update_progress(run_id, progress_pct)`
  - `start_step(run_id, step_name, step_order)`
  - `end_step_ok(run_id, step_order)`
  - `end_step_failed(run_id, step_order, error_message)`
- **Context Manager:** `StepLogger` para instrumentação automática de blocos de código

---

### 📁 `utils/`
Agrupa funções auxiliares e reutilizáveis.

#### **`business_calendar.py`**
- **Funções:**
  - `deve_executar_processo()`: verifica se hoje é o 3º dia útil
  - `calcular_datas_mes_anterior()`: retorna (data_inicial, data_final) do mês anterior
  - `eh_dia_util(data)`: verifica se data é dia útil (seg-sex, exceto feriados)
  - `terceiro_dia_util_mes(ano, mes)`: calcula 3º dia útil do mês
- **Calendário de feriados:** lista hardcoded de feriados nacionais
- **Bypass:** variável `FORCAR_EXECUCAO=true` força execução em qualquer data

#### **`logger.py`**
- **Função:** `setup_logger(process_name)`
- **Responsabilidades:**
  - Configuração de logging estruturado (console + arquivo)
  - Formato: `[%(asctime)s] [%(levelname)s] [run_id:%(run_id)s] %(message)s`
  - Arquivo: `logs/processo_{process_name}_{timestamp}_pid{pid}_runid_{run_id}.log`
  - Filtros customizados para adicionar run_id dinamicamente

---

### 📁 `tests/`
Diretório de testes unitários e de integração.

- **`test_data_sample.py`**: dados de amostra compartilhados (25 centros de custo)
- **`test_excel_generation.py`**: valida geração de Excel com colunas corretas
- **`test_worddata_structure.py`**: valida estrutura WordData e balanceamento contábil
- **`test_execution.py`**: teste end-to-end com DRY_RUN e FORCAR_EXECUCAO
- **`run_all_tests.py`**: executa todos os testes sequencialmente

Documentação detalhada: `tests/README.md`

---

### 📁 `logs/`
Diretório gerado automaticamente pela função `setup_logger()`.

- Cada execução cria um arquivo único contendo timestamp, PID e run_id.
- Utilizado tanto para auditoria quanto para depuração.
- **Exemplo:** `processo_ctb-reclassificar_20241223_143052_pid12345_runid_a1b2c3.log`

---

## 3. Arquivos na Raiz do Projeto

- **`main.py`**: ponto de entrada da aplicação; carrega .env, configura logging e chama `run()`.
- **`.gitignore`**: define arquivos ignorados (config/.env, logs/, *.xlsx, test_database.py, etc).
- **`requirements.txt`**: dependências essenciais (requests, pandas, openpyxl, python-dotenv, psycopg2-binary).
- **`requirements-dev.txt`**: dependências de desenvolvimento (black, mypy, pytest, bandit).
- **`pyproject.toml`**: configurações de ferramentas (black, isort, mypy, bandit).

---

## 4. Fluxo de Dados

### Entrada
1. **API de Reclassificação** retorna JSON:
```json
[
  {
    "CENTROCUSTO": "11102001",
    "CONTA": "1010101050",
    "DESCRICAO": "Diretoria Financeira",
    "VALORCREDITO": -76890.50
  },
  {
    "CENTROCUSTO": "12200001",
    "CONTA": "1010101050",
    "DESCRICAO": "Diretoria Operacional",
    "VALORCREDITO": 5000.00
  },
  ...
]
```

### Processamento
2. **Modelo:** `processar_reclassificacao()` transforma dados:
   - Identifica débito (11102001, valor negativo)
   - Remove 12200001 dos créditos
   - Calcula VALORDEBITO = soma(VALORCREDITO dos créditos)

3. **Modelo:** `montar_word_data()` gera estrutura WordData:
```json
[
  {
    "CENTROCUSTO": "12300001",
    "CONTACREDITO": "1010101050",
    "VALORCREDITO": 12345.67
  },
  ...
  {
    "CENTROCUSTO": "11102001",
    "CONTADEBITO": "1010101050",
    "VALORDEBITO": 76890.50
  }
]
```

### Saída
4. **API MegaIntegrador:** recebe WordData e cria lançamentos contábeis
5. **SharePoint:** recebe Excel com todos os dados (créditos + débito)
6. **Teams:** recebe notificação com resumo e link do Excel

---

## 5. Telemetria e Observabilidade

### Banco de Dados (PostgreSQL/Supabase)

#### Schema: `public.execution_runs`
```sql
CREATE TABLE public.execution_runs (
    run_id UUID PRIMARY KEY,
    process_name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    status VARCHAR(50) NOT NULL,  -- RUNNING, COMPLETED, FAILED, CANCELLED
    progress_pct FLOAT DEFAULT 0,
    duration_sec INT,
    error_message TEXT
);
```

#### Schema: `public.execution_steps`
```sql
CREATE TABLE public.execution_steps (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES public.execution_runs(run_id),
    step_name VARCHAR(255) NOT NULL,
    step_order INT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    status VARCHAR(50) NOT NULL,  -- RUNNING, COMPLETED, FAILED
    error_message TEXT
);
```

### Logs Estruturados
- **Formato:** `[timestamp] [level] [run_id:uuid] mensagem`
- **Níveis:** DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Rotação:** não implementada (arquivos únicos por execução)

---

## 6. Segurança

### Credenciais
- **NUNCA** versionar o arquivo `config/.env`
- Usar `.env.example` como template (sem valores reais)
- Certificados PFX armazenados no SharePoint (não no código)

### APIs
- Tokens de autenticação em variáveis de ambiente
- HTTPS obrigatório para todas as chamadas
- Service Principal com permissões mínimas necessárias

### Banco de Dados
- Connection string em variável de ambiente
- Pool de conexões com limite (maxconn=5)
- Tratamento de erros sem expor credenciais nos logs

---

## 7. Manutenção e Evolução

### Adicionar Nova Etapa
1. Criar função no módulo apropriado (`services/` ou `models/`)
2. Adicionar chamada em `reclassification_controller.py`
3. Instrumentar com `StepLogger(run_id, "nome_step", ordem)`
4. Atualizar progresso com `update_progress(run_id, percentual)`
5. Atualizar documentação (`process_overview.md`)

### Adicionar Novo Teste
1. Criar arquivo em `tests/test_*.py`
2. Usar dados de `test_data_sample.py`
3. Adicionar ao `run_all_tests.py`
4. Documentar em `tests/README.md`

### Debug de Problemas
1. Consultar logs em `/logs` usando run_id
2. Consultar banco de dados:
```sql
SELECT * FROM public.execution_runs WHERE run_id = 'uuid';
SELECT * FROM public.execution_steps WHERE run_id = 'uuid' ORDER BY step_order;
```
3. Executar em modo DRY_RUN para reproduzir sem impacto

---

## 8. Dependências Externas

### APIs
- **API de Reclassificação:** coleta de dados contábeis
- **API MegaIntegrador:** envio de lançamentos contábeis
- **Microsoft Graph API:** upload para SharePoint
- **Teams Webhook:** notificações

### Serviços
- **Supabase PostgreSQL:** telemetria (opcional)
- **SharePoint Online:** armazenamento de relatórios
- **Microsoft Teams:** comunicação com equipe

---

Documento atualizado para refletir a estrutura e responsabilidades atuais do projeto ctb-reclassificar_conta_de_juros_cc_14.