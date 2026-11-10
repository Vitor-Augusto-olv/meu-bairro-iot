"""Recria eval/dataset_robustez a partir do eval/dataset ATUAL (rode depois de revisar as fotos).
Uso: python -m eval.degradar
"""
import shutil
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

RAIZ = Path(__file__).parent
SAIDA = RAIZ / 'dataset_robustez'

if SAIDA.exists():
    shutil.rmtree(SAIDA)

total = 0
for pasta in sorted((RAIZ / 'dataset').iterdir()):
    if not pasta.is_dir() or pasta.name == 'NENHUM':
        continue
    destino = SAIDA / pasta.name
    destino.mkdir(parents=True)
    for arq in sorted(pasta.iterdir()):
        if arq.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
            continue
        img = Image.open(arq).convert('RGB')
        img.filter(ImageFilter.GaussianBlur(6)).save(destino / f'{arq.stem}_borrada.jpg')
        ImageEnhance.Brightness(img).enhance(0.25).save(destino / f'{arq.stem}_escura.jpg')
        total += 2
print(f'{total} imagens degradadas criadas em eval/dataset_robustez')
