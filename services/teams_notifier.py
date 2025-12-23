"""
Notificações via Microsoft Teams (Power Automate).

Envia notificações formatadas em HTML para o Teams via webhook.
"""
import logging
from datetime import datetime
from typing import Optional
import pandas as pd
from utils.http_client import HTTPClient
from utils.sanitizer import sanitize_error_for_notification
from config.settings import get_power_automate_webhook, get_dado_comparativo_tabela


# Cliente HTTP para notificações
http_client = HTTPClient()
SESSION = http_client.get_session()


def enviar_notificacao_teams(mensagem_html: str, tipo: str = "INFO") -> bool:
    """
    Envia notificação para o Teams via Power Automate webhook.

    Args:
        mensagem_html: Conteúdo HTML da mensagem
        tipo: Tipo da notificação (ERRO, AVISO, SUCESSO, INFO)

    Returns:
        bool: True se sucesso, False se erro
    """
    from config.settings import is_dry_run, test_sharepoint_teams

    # Modo DRY_RUN (mas não em modo teste): simular notificação
    if is_dry_run() and not test_sharepoint_teams():
        logging.info(f"[DRY_RUN] Simulando notificação Teams (tipo: {tipo})...")
        logging.info(f"[DRY_RUN] Mensagem: {mensagem_html[:100]}...")
        return True

    webhook_url = get_power_automate_webhook()

    if not webhook_url:
        logging.error("POWER_AUTOMATE_WEBHOOK_URL não configurado no .env")
        return False

    # Remover quebras de linha do HTML
    mensagem_html_limpa = mensagem_html.replace('\n', '').replace('  ', ' ').strip()

    payload = {
        "messageBody": mensagem_html_limpa
    }

    try:
        response = SESSION.post(webhook_url, json=payload, timeout=30)
        response.raise_for_status()
        logging.info(f"Notificação enviada ao Teams via Power Automate ({tipo})")
        return True
    except Exception as e:
        logging.error(f"Erro ao enviar notificação ao Teams: {e}")
        logging.error(f"Webhook URL: {webhook_url[:80]}...")
        logging.error(f"Payload enviado (primeiros 200 chars): {str(payload)[:200]}...")
        logging.error("Verifique se POWER_AUTOMATE_WEBHOOK_URL está correto no .env")
        logging.error("Verifique se o fluxo do Power Automate aceita o campo 'messageBody'")
        return False


def notificar_erro_api(erro_msg: str) -> bool:
    """
    Notifica erro de API no Teams.

    Args:
        erro_msg: Mensagem de erro (será sanitizada)

    Returns:
        bool: True se sucesso, False se erro
    """
    hoje = datetime.now().strftime('%d/%m/%Y')

    # Sanitizar mensagem de erro
    erro_sanitizado = sanitize_error_for_notification(erro_msg, max_length=300)

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Calibri, sans-serif; font-size: 11pt; }}
            .erro {{ color: #d32f2f; font-weight: bold; }}
        </style>
    </head>
    <body>
        <p class="erro">❌ Falha ctb_Reclassificar conta de juros cc 14</p>
        <p><b>Erro API Reclassificar cc 14:</b> {erro_sanitizado}</p>
        <p><b>Executado em:</b> {hoje}</p>
    </body>
    </html>
    """

    return enviar_notificacao_teams(html, tipo="ERRO")


def notificar_sem_dados() -> bool:
    """
    Notifica que a API não retornou dados.

    Returns:
        bool: True se sucesso, False se erro
    """
    hoje = datetime.now().strftime('%d/%m/%Y')

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Calibri, sans-serif; font-size: 11pt; }}
            .aviso {{ color: #f57c00; font-weight: bold; }}
        </style>
    </head>
    <body>
        <p class="aviso">⚠️ Sem dados retornados na chamada de ctb_Reclassificar conta de juros cc 14</p>
        <p><b>API Reclassificar cc 14</b></p>
        <p><b>Realizada em:</b> {hoje}</p>
    </body>
    </html>
    """

    return enviar_notificacao_teams(html, tipo="AVISO")


def gerar_tabela_resumo(df_creditos: pd.DataFrame, diretoria_financeira_info: Optional[dict]) -> str:
    """
    Gera tabela HTML de resumo dos lançamentos.

    Args:
        df_creditos: DataFrame com os centros de custo de crédito
        diretoria_financeira_info: Dict com informações da Diretoria Financeira

    Returns:
        str: HTML da tabela formatada
    """
    conta_reduzido = get_dado_comparativo_tabela()

    # Construir linhas da tabela
    linhas_html = ""

    # Adicionar linhas para cada centro de custo (com crédito)
    for idx, row in df_creditos.iterrows():
        valor_credito = f"R$ {row['VALORCREDITO']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        linhas_html += f"""
        <tr>
            <td>{row['CENTROCUSTO']}</td>
            <td>{conta_reduzido}</td>
            <td></td>
            <td>{valor_credito}</td>
        </tr>
        """

    # Adicionar linha da Diretoria Financeira (com débito)
    if diretoria_financeira_info:
        valor_debito = f"R$ {diretoria_financeira_info['VALOR']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        linhas_html += f"""
        <tr>
            <td>{diretoria_financeira_info['CENTROCUSTO']}</td>
            <td></td>
            <td>{conta_reduzido}</td>
            <td>{valor_debito}</td>
        </tr>
        """

    return linhas_html


def notificar_sucesso(df_creditos: pd.DataFrame, diretoria_financeira_info: Optional[dict], link_arquivo: str = "") -> bool:
    """
    Notifica sucesso do processo com tabela de resumo no Teams.

    Args:
        df_creditos: DataFrame com os centros de custo de crédito
        diretoria_financeira_info: Dict com informações da Diretoria Financeira
        link_arquivo: Link do arquivo no SharePoint

    Returns:
        bool: True se sucesso, False se erro
    """
    hoje = datetime.now().strftime('%d/%m/%Y')
    conta_reduzido = get_dado_comparativo_tabela()

    # Gerar linhas da tabela
    tabela_linhas = gerar_tabela_resumo(df_creditos, diretoria_financeira_info)

    # Adicionar link do arquivo se disponível
    link_html = ""
    if link_arquivo:
        link_html = f'<p><a href="{link_arquivo}" target="_blank" style="color: #1976d2; text-decoration: underline; font-weight: bold;">📎 Clique aqui para acessar o Relatório no SharePoint</a></p>'

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Calibri, sans-serif; font-size: 11pt; }}
            .sucesso {{ color: #2e7d32; font-weight: bold; }}
            table {{ border-collapse: collapse; width: auto; max-width: 800px; margin-top: 15px; }}
            th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
            td:nth-child(4) {{ text-align: right; }}
            a {{ color: #1976d2; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <p class="sucesso">✅ ctb-Reclassificar conta de juros cc 14 {conta_reduzido} de {hoje}:</p>
        {link_html}
        <table>
            <thead>
                <tr>
                    <th>CENTROCUSTO</th>
                    <th>C</th>
                    <th>D</th>
                    <th>VALORRAZÃO</th>
                </tr>
            </thead>
            <tbody>
{tabela_linhas}
            </tbody>
        </table>
    </body>
    </html>
    """

    return enviar_notificacao_teams(html, tipo="SUCESSO")