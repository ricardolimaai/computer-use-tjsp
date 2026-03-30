#!/usr/bin/env python3
"""Monitor de processos do TJSP — ponto de entrada."""

import argparse
import json
import sys

from agent import consultar_processo
from storage import salvar, comparar


def main():
    parser = argparse.ArgumentParser(
        description="Monitora processos no TJSP (e-SAJ)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python main.py 1234567-89.2024.8.26.0100\n"
            "  python main.py 1234567-89.2024.8.26.0100 --visible\n"
        ),
    )
    parser.add_argument("processo", help="Número do processo (formato CNJ completo)")
    parser.add_argument(
        "--visible", action="store_true",
        help="Abre o navegador visível (útil para resolver captcha)",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Saída em JSON puro (sem formatação)",
    )
    args = parser.parse_args()

    print(f"Consultando processo {args.processo}...")

    try:
        dados = consultar_processo(args.processo, headless=not args.visible)
    except ValueError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        if "CAPTCHA" in str(e):
            print("DICA: Use --visible para abrir o navegador e resolver o captcha manualmente.", file=sys.stderr)
        sys.exit(2)

    # Compara com execução anterior antes de salvar
    diff = comparar(args.processo, dados)

    # Salva nova consulta
    filepath = salvar(args.processo, dados)

    if args.json_output:
        resultado = {"dados": dados, "diff": diff, "arquivo": filepath}
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return

    # Saída formatada
    print(f"\n{'='*60}")
    print(f"Processo: {dados['numero']}")
    print(f"Classe:   {dados.get('classe') or '—'}")
    print(f"Assunto:  {dados.get('assunto') or '—'}")
    print(f"Status:   {dados.get('status') or '—'}")
    print(f"Foro:     {dados.get('foro') or '—'}")
    print(f"Vara:     {dados.get('vara') or '—'}")
    print(f"Juiz:     {dados.get('juiz') or '—'}")
    print(f"{'='*60}")

    if dados.get("partes"):
        print("\nPartes:")
        for p in dados["partes"]:
            print(f"  {p['tipo']}: {p['nome']}")

    if dados.get("movimentacoes"):
        print(f"\nÚltimas movimentações ({len(dados['movimentacoes'])} total):")
        for mov in dados["movimentacoes"][:10]:
            print(f"  [{mov['data']}] {mov['titulo']}")

    # Mostra diff
    if diff is None:
        print(f"\nPrimeira consulta — dados salvos em {filepath}")
    elif not diff["mudancas"]:
        print("\nNenhuma mudança desde a última consulta.")
    else:
        print(f"\n{'!'*60}")
        print(f"MUDANÇAS desde {diff['timestamp_anterior']}:")
        if "status" in diff["mudancas"]:
            s = diff["mudancas"]["status"]
            print(f"  Status: {s['antes']} → {s['agora']}")
        if "novas_movimentacoes" in diff["mudancas"]:
            print(f"  Novas movimentações:")
            for mov in diff["mudancas"]["novas_movimentacoes"]:
                print(f"    [{mov['data']}] {mov['titulo']}")
        print(f"{'!'*60}")

    print(f"\nDados salvos em {filepath}")


if __name__ == "__main__":
    main()
