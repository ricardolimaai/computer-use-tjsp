"""Agente que consulta processos no e-SAJ do TJSP via Playwright."""

import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

TJSP_URL = "https://esaj.tjsp.jus.br/cpopg/open.do"


def _parse_numero(numero: str) -> tuple[str, str]:
    """Separa número unificado em (primeiros 15 dígitos, foro 4 dígitos).

    Aceita formatos:
      1234567-89.2024.8.26.0100
      1234567-89.2024.8.26.0100
    """
    limpo = re.sub(r"[^\d]", "", numero)
    if len(limpo) != 20:
        raise ValueError(
            f"Número de processo inválido ({len(limpo)} dígitos, esperado 20): {numero}"
        )
    # Campo 1: NNNNNNN-DD.AAAA  (13 chars formatados, 13 dígitos sem pontuação)
    # Campo 2: FFFF (foro, últimos 4 dígitos)
    parte1 = f"{limpo[:7]}-{limpo[7:9]}.{limpo[9:13]}"
    foro = limpo[16:20]
    return parte1, foro


def consultar_processo(numero: str, headless: bool = True) -> dict:
    """Consulta um processo no TJSP e retorna dados estruturados.

    Returns:
        dict com chaves: numero, classe, assunto, area, status, partes, movimentacoes
    Raises:
        RuntimeError: se captcha detectado ou erro de navegação
        ValueError: se número de processo inválido
    """
    parte1, foro = _parse_numero(numero)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        try:
            page.goto(TJSP_URL, timeout=30000)
            page.wait_for_load_state("domcontentloaded")

            # Preenche número do processo
            page.fill("#numeroDigitoAnoUnificado", parte1)
            page.fill("#foroNumeroUnificado", foro)

            # Submete busca
            page.click("#botaoConsultarProcessos")

            # Aguarda resultado ou erro
            try:
                page.wait_for_selector(
                    "#tabelaTodasMovimentacoes, #mensagemRetorno, .captchaChallengeField, #captchaMensagem",
                    timeout=15000,
                )
            except PlaywrightTimeout:
                raise RuntimeError(
                    "Timeout aguardando resultado. O site pode estar fora do ar."
                )

            # Verifica captcha
            if page.query_selector(".captchaChallengeField") or page.query_selector("#captchaMensagem"):
                raise RuntimeError(
                    "CAPTCHA detectado! O TJSP está exigindo verificação humana. "
                    "Tente novamente em alguns minutos ou use headless=False para resolver manualmente."
                )

            # Verifica mensagem de erro (processo não encontrado)
            msg_erro = page.query_selector("#mensagemRetorno")
            if msg_erro:
                texto_erro = msg_erro.inner_text().strip()
                if texto_erro:
                    raise RuntimeError(f"Erro do TJSP: {texto_erro}")

            # Extrai dados do processo
            dados = _extrair_dados(page)
            dados["numero"] = numero
            return dados

        finally:
            browser.close()


def _extrair_dados(page) -> dict:
    """Extrai dados estruturados da página de resultado."""
    dados = {}

    # Dados principais (tabela de cabeçalho)
    campos = {
        "classe": "#classeProcesso",
        "assunto": "#assuntoProcesso",
        "area": "#areaProcesso span",
        "juiz": "#juizProcesso",
        "valor_acao": "#valorAcaoProcesso",
        "foro": "#foroProcesso",
        "vara": "#varaProcesso",
    }
    for chave, seletor in campos.items():
        el = page.query_selector(seletor)
        dados[chave] = el.inner_text().strip() if el else None

    # Status / situação
    situacao_el = page.query_selector("#labelSituacaoProcesso")
    dados["status"] = situacao_el.inner_text().strip() if situacao_el else None

    # Partes
    dados["partes"] = _extrair_partes(page)

    # Movimentações — tenta expandir todas primeiro
    btn_todas = page.query_selector("#linkmovalialialialialialialialialialialialialialialialialialialialialialialialia")
    if not btn_todas:
        btn_todas = page.query_selector("a.linkMovVinc  , #linkMovVincTodas, a[onclick*='todas']")
    if btn_todas:
        try:
            btn_todas.click()
            page.wait_for_timeout(1000)
        except Exception:
            pass

    dados["movimentacoes"] = _extrair_movimentacoes(page)

    return dados


def _extrair_partes(page) -> list[dict]:
    """Extrai partes do processo."""
    partes = []
    tabela = page.query_selector("#tablePartesPrincipais")
    if not tabela:
        tabela = page.query_selector("#tableTodasPartes")
    if not tabela:
        return partes

    linhas = tabela.query_selector_all("tr")
    for linha in linhas:
        tipo_el = linha.query_selector(".tipoDeParticipacao")
        nome_el = linha.query_selector(".nomeParteEAdvogado")
        if tipo_el and nome_el:
            partes.append({
                "tipo": tipo_el.inner_text().strip().rstrip(":"),
                "nome": nome_el.inner_text().strip(),
            })
    return partes


def _extrair_movimentacoes(page) -> list[dict]:
    """Extrai movimentações do processo."""
    movimentacoes = []

    # Tenta tabela completa primeiro, senão a parcial
    tabela = page.query_selector("#tabelaTodasMovimentacoes")
    if not tabela:
        tabela = page.query_selector("#tabelaUltimasMovimentacoes")
    if not tabela:
        return movimentacoes

    linhas = tabela.query_selector_all("tr")
    for linha in linhas:
        data_el = linha.query_selector("td.dataMovimentacao, td.dataMovimentacaoProcesso")
        desc_el = linha.query_selector("td.descricaoMovimentacao, td.descricaoMovimentacaoProcesso")
        if data_el and desc_el:
            # Título é o primeiro span/strong, descrição é o texto completo
            titulo_el = desc_el.query_selector("a, span")
            titulo = titulo_el.inner_text().strip() if titulo_el else ""
            descricao_completa = desc_el.inner_text().strip()

            movimentacoes.append({
                "data": data_el.inner_text().strip(),
                "titulo": titulo or descricao_completa.split("\n")[0],
                "descricao": descricao_completa,
            })

    return movimentacoes
