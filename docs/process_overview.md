# Visão Geral do Processo

## 1. Visão Geral do Projeto

O projeto **ctb-reclassificar_conta_de_juros_cc_14** automatiza a reclassificação contábil mensal de juros creditados na conta CC14. A solução substitui o processo manual de coleta, processamento e lançamento contábil, garantindo precisão e rastreabilidade completa das operações financeiras do Grupo Odilon Santos.

**Departamentos envolvidos:** Contabilidade
**Autor:** Yasmim Augusto dos Santos - Núcleo de Excelência - GOS
**Data de criação:** Dezembro/2025

### Valor de Negócio
- **Redução de erros:** elimina reclassificações manuais suscetíveis a falhas humanas.
- **Aumento de eficiência:** processo que levava horas agora é executado automaticamente em minutos.
- **Conformidade e auditoria:** logs detalhados e registro em banco de dados com rastreabilidade completa (run_id, steps, timestamps).
- **Visibilidade:** notificações automáticas no Teams com resumo executivo e acesso direto aos relatórios.

---

## 2. Principais Características Técnicas

- **Execução agendada:** disparo automático no 3º dia útil de cada mês, com validação de calendário de feriados.
- **Processamento estruturado em etapas:** 9 steps independentes com telemetria individual (início, fim, status, erros).
- **Telemetria em PostgreSQL (Supabase):** registro opcional de todas as execuções e steps com progresso em tempo real.
- **Modo DRY_RUN:** permite simulação completa do processo sem executar operações reais (útil para testes).
- **Tratamento robusto de erros:** cada etapa valida seu resultado antes de prosseguir; falhas bloqueiam execução e notificam equipe.
- **Logging estruturado:** arquivos de log únicos por execução (`processo_ctb-reclassificar_*.log`) com run_id para correlação.
- **Separação de ambientes:** configuração via `.env` permite alternar entre dev/prod sem alterar código.

---

## 3. Fluxo do Processo (9 Etapas)

### **Etapa 1: Verificação de Dia Útil**
- Valida se hoje é o 3º dia útil do mês atual.
- Considera calendário de feriados nacionais.
- Se não for o dia de execução, encerra o processo sem registrar no banco de dados.
- **Bypass:** variável `FORCAR_EXECUCAO=true` permite execução em qualquer data (para testes).

### **Etapa 2: Cálculo de Datas**
- Calcula o período do mês anterior:
  - `data_inicial`: primeiro dia do mês anterior
  - `data_final`: último dia do mês anterior
- Exemplo: se hoje é 03/01/2025 (3º dia útil de janeiro), processa dezembro/2024 completo.

### **Etapa 3: Coleta de Dados via API**
- Chama a **API de Reclassificação** passando data_inicial e data_final.
- Recebe lista de centros de custo com valores de juros creditados na CC14.
- **Tratamento de erros:** se API falha, encerra processo e notifica equipe via Teams.

### **Etapa 4: Processamento de Dados**
- Aplica regras de negócio contábeis:
  - Separa créditos (centros de custo que receberão os juros)
  - Identifica débito (Diretoria Financeira - centro de custo 11102001)
  - Remove Diretoria Operacional (12200001) dos créditos
- Gera 3 outputs:
  - `df_creditos`: DataFrame com centros de crédito
  - `diretoria_financeira_info`: informações do lançamento de débito
  - `df_completo`: DataFrame completo para Excel (créditos + débito)

### **Etapa 5: Montagem de WordData**
- Transforma os dados processados no formato **WordData** (JSON estruturado).
- WordData contém:
  - Lista de itens de lançamento (créditos + débito)
  - Cada item possui: centro de custo, conta contábil, valor, tipo (C/D)
- Validações automáticas:
  - Soma dos créditos = valor do débito (balanceamento contábil)
  - Todos os campos obrigatórios preenchidos

### **Etapa 6: Envio de Lançamentos Contábeis**
- Envia o WordData para a **API MegaIntegrador** (sistema contábil).
- API cria os lançamentos contábeis no sistema ERP.
- **Tratamento de erros:** se envio falha, encerra processo e notifica equipe.
- **Modo DRY_RUN:** simula envio sem executar de verdade.

### **Etapa 7: Autenticação Microsoft Graph**
- Obtém token de acesso OAuth2 para Microsoft Graph API.
- Usa credenciais de Service Principal (CLIENT_ID, CLIENT_SECRET, TENANT_ID).
- Token é usado para operações no SharePoint na próxima etapa.

### **Etapa 8: Upload para SharePoint**
- Gera planilha Excel com dados completos (créditos + débito).
- Faz upload do Excel para pasta específica no SharePoint.
- Retorna link público do arquivo para compartilhamento.
- **Tratamento de erros:** se upload falha, processo continua (não é crítico) mas registra warning no log.

### **Etapa 9: Notificação via Teams**
- Envia mensagem formatada para canal do Microsoft Teams via webhook.
- Mensagem contém:
  - Resumo executivo (quantidade de centros de custo, valores totais)
  - Link para o arquivo Excel no SharePoint
  - Data/hora da execução
  - Run_id para rastreabilidade
- **Modo TEST_SHAREPOINT_TEAMS:** permite desabilitar notificação em testes.

---

## 4. Telemetria e Monitoramento

### Registro em Banco de Dados (PostgreSQL/Supabase)
Todas as execuções são registradas em duas tabelas:

#### Tabela: `execution_runs`
- `run_id` (UUID único)
- `process_name` ("ctb-reclassificar_conta_de_juros_cc_14")
- `started_at`, `ended_at`
- `status` (RUNNING, COMPLETED, FAILED, CANCELLED)
- `progress_pct` (0-100%)
- `duration_sec`
- `error_message` (se houver)

#### Tabela: `execution_steps`
- `run_id` (FK para execution_runs)
- `step_name` (nome da etapa)
- `step_order` (1-9)
- `started_at`, `ended_at`
- `status` (RUNNING, COMPLETED, FAILED)
- `error_message` (se houver)

### Logs em Arquivo
- Diretório: `/logs`
- Formato: `processo_ctb-reclassificar_<timestamp>_pid<pid>_runid_<run_id>.log`
- Cada linha contém: timestamp, nível (INFO/WARNING/ERROR/CRITICAL), run_id, mensagem

---

## 5. Variáveis de Ambiente Críticas

### Execução
- `FORCAR_EXECUCAO`: força execução em qualquer data (para testes)
- `DRY_RUN`: simula operações sem executar de verdade
- `TEST_SHAREPOINT_TEAMS`: desabilita notificações em testes

### APIs Externas
- `API_RECLASSIFICACAO_URL`, `API_RECLASSIFICACAO_TOKEN`
- `API_MEGAINTEGRADOR_URL`, `API_MEGAINTEGRADOR_TOKEN`

### Microsoft Graph/SharePoint
- `TENANT_ID`, `CLIENT_ID`, `CLIENT_SECRET`
- `GRAPH_DRIVE_ID`, `GRAPH_FOLDER_ID`

### Teams Webhook
- `TEAMS_WEBHOOK_URL`

### Telemetria (Opcional)
- `EXECUTION_DB_DSN`: connection string do PostgreSQL

---

## 6. Cenários de Uso

### Execução Normal (Produção)
1. Agendador (Task Scheduler/Cron) dispara `main.py` diariamente
2. Script verifica se hoje é o 3º dia útil
3. Se sim, executa processo completo
4. Se não, encerra sem fazer nada

### Execução Forçada (Testes)
```bash
# No terminal ou no .env:
set FORCAR_EXECUCAO=true
python main.py
```

### Execução em Modo Simulação
```bash
set DRY_RUN=true
set FORCAR_EXECUCAO=true
python main.py
```

---

## 7. Tratamento de Erros e Recuperação

### Falhas Críticas (Encerram o Processo)
- API de Reclassificação não responde ou retorna erro
- Erro no processamento de dados (regras de negócio)
- Falha ao enviar lançamentos contábeis (MegaIntegrador)
- Falha na autenticação Microsoft Graph

**Ações tomadas:**
1. Registra erro no banco (status=FAILED, error_message)
2. Grava detalhes no log
3. Notifica equipe via Teams (se possível)
4. Encerra processo com exit code 1

### Falhas Não-Críticas (Processo Continua)
- Falha no upload para SharePoint
- Falha ao enviar notificação no Teams

**Ações tomadas:**
1. Registra warning no log
2. Continua execução das próximas etapas

---

## 8. Documentação Adicional

- **Guia Técnico Detalhado:** docs/technical_details.md
- **README Geral:** docs/README.md
- **Testes e Validações:** tests/README.md