"""Avalia a etapa de visão no conjunto de teste e (opcional) a geração de texto.

Estrutura esperada: eval/dataset/<CATEGORIA>/*.jpg  com as pastas
BURACO, ILUMINACAO, LIXO, ALAGAMENTO, CALCADA e NENHUM (fotos sem problema, desfocadas, com rosto...).
Uso: python -m eval.avaliar [--com-llm] [--pasta dataset_robustez]
"""
import json
import sys
import time
from pathlib import Path

from sklearn.metrics import classification_report, confusion_matrix

from app import geracao, visao

PASTA = sys.argv[sys.argv.index('--pasta') + 1] if '--pasta' in sys.argv else 'dataset'
RAIZ = Path(__file__).parent / PASTA
CLASSES = list(visao.CLASSES)


def main(com_llm: bool):
    reais, previstas, tempos, erros = [], [], [], []
    for classe in CLASSES:
        for arq in sorted((RAIZ / classe).glob('*')):
            if arq.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
                continue
            t0 = time.perf_counter()
            r = visao.classificar(arq.read_bytes())
            tempos.append(time.perf_counter() - t0)
            reais.append(classe)
            previstas.append(r['categoria'])
            if r['categoria'] != classe:
                erros.append({'arquivo': f'{classe}/{arq.name}', 'previsto': r['categoria'], 'confianca': r['confianca']})
    if not reais:
        sys.exit('Nenhuma imagem encontrada em eval/dataset/<CATEGORIA>/')

    acuracia = sum(a == b for a, b in zip(reais, previstas)) / len(reais)
    saida = {
        'imagens': len(reais),
        'acuracia': round(acuracia, 3),
        'tempo_medio_s': round(sum(tempos) / len(tempos), 2),
        'relatorio': classification_report(reais, previstas, labels=CLASSES, zero_division=0, output_dict=True),
        'matriz_confusao': {'classes': CLASSES, 'valores': confusion_matrix(reais, previstas, labels=CLASSES).tolist()},
        'erros': erros,
    }
    if com_llm:
        origens = [geracao.gerar(c, 0.9)[1] for c in CLASSES if c != 'NENHUM' for _ in range(3)]
        saida['geracao_llm_valida'] = round(origens.count('llm') / len(origens), 2)

    (Path(__file__).parent / f'resultados_{PASTA}.json').write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Imagens: {saida['imagens']} | Acurácia: {saida['acuracia']:.1%} | Tempo médio: {saida['tempo_medio_s']}s")
    print(classification_report(reais, previstas, labels=CLASSES, zero_division=0))
    print('Erros:', *[f"\n  {e['arquivo']} -> {e['previsto']} ({e['confianca']})" for e in erros])


if __name__ == '__main__':
    main('--com-llm' in sys.argv)
