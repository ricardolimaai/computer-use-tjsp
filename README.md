# Monitor de Processos TJSP

Agente Python que consulta e monitora processos judiciais no e-SAJ do Tribunal de Justiça de São Paulo (esaj.tjsp.jus.br) usando Playwright.

## O Problema

Acompanhar processos judiciais no TJSP exige acessar manualmente o portal e-SAJ, buscar pelo número do processo e verificar se houve novas movimentações. Para quem acompanha múltiplos processos, isso consome tempo e é fácil perder uma atualização importante.

## A Solução

Um agente automatizado que:

1. Acessa o portal e-SAJ via browser automatizado (Playwright)
2. Busca o processo pelo número CNJ
3. Extrai dados estruturados: status, partes, movimentações
4. Salva em JSON local com timestamp
5. Compara com a consulta anterior e destaca o que mudou

## Instalação

```bash
# Clone ou copie o projeto
cd computer-use-tjsp

# Crie um virtualenv (recomendado)
python3 -m venv venv
source venv/bin/activate

# Instale dependências
pip install -r requirements.txt

# Instale os browsers do Playwright
playwright install chromium
```

## Uso

```bash
# Consulta básica
python main.py 1234567-89.2024.8.26.0100

# Com navegador visível (para resolver captcha)
python main.py 1234567-89.2024.8.26.0100 --visible

# Saída em JSON
python main.py 1234567-89.2024.8.26.0100 --json
```

### Formato do número

Use o formato CNJ completo com 20 dígitos:

```
NNNNNNN-DD.AAAA.J.TR.OOOO
```

Exemplo: `1234567-89.2024.8.26.0100`

## Estrutura do projeto

```
computer-use-tjsp/
├── main.py           # Ponto de entrada CLI
├── agent.py          # Lógica de scraping com Playwright
├── storage.py        # Persistência em JSON
├── data/             # Dados salvos (criado automaticamente)
├── requirements.txt
└── README.md
```

## Captcha

O TJSP pode exigir captcha em momentos de alto tráfego. Quando isso acontece, o agente avisa e sugere usar `--visible` para resolver manualmente.

## Dados salvos

Cada processo gera um arquivo JSON em `data/` com o histórico de todas as consultas. Exemplo:

```json
[
  {
    "timestamp": "2024-01-15T10:30:00",
    "dados": {
      "numero": "1234567-89.2024.8.26.0100",
      "classe": "Procedimento Comum Cível",
      "status": "Em andamento",
      "movimentacoes": [...]
    }
  }
]
```

Na segunda execução em diante, o agente mostra as mudanças desde a última consulta.
