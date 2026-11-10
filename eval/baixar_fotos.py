"""Monta o conjunto de teste automaticamente a partir do Wikimedia Commons (só licenças livres).

Antes: defina seu e-mail (a Wikimedia exige contato no User-Agent):
  $env:COMMONS_CONTATO="seuemail@exemplo.com"
Uso: python -m eval.baixar_fotos [--por-classe 6] [--so ALAGAMENTO]
--so refaz apenas uma categoria (apaga as fotos antigas dela e mantém as outras).
- Baixa fotos para eval/dataset/<CATEGORIA>/ e registra autor e licença em eval/FONTES.csv.
- Gera versões borradas e escuras em eval/dataset_robustez/ (teste de situações de falha).
A busca é por texto, então CONFIRA as pastas e apague fotos que não combinam com a categoria.
"""
import csv
import io
import os
import re
import sys
import time
from pathlib import Path

import httpx
from PIL import Image, ImageEnhance, ImageFilter

API = 'https://commons.wikimedia.org/w/api.php'
LIVRES = ('CC', 'Public domain', 'PD')
RAIZ = Path(__file__).parent

BUSCAS = {
    'BURACO': ['pothole road', 'pothole damaged asphalt street'],
    'ILUMINACAO': ['broken street light', 'leaning utility pole', 'fallen street lamp'],
    'LIXO': ['illegal dumping street', 'garbage pile street'],
    'ALAGAMENTO': ['flooded street car water', 'street flooding heavy rain', 'enchente rua alagada', 'alagamento avenida chuva'],
    'CALCADA': ['broken sidewalk', 'cracked pavement sidewalk'],
    'NENHUM': ['empty city street', 'living room interior', 'selfie', 'car license plate'],
}


def buscar(cliente, termo):
    r = cliente.get(API, params={
        'action': 'query', 'generator': 'search', 'gsrnamespace': 6, 'gsrsearch': termo, 'gsrlimit': 30,
        'prop': 'imageinfo', 'iiprop': 'url|mime|extmetadata', 'iiurlwidth': 800, 'format': 'json'})
    r.raise_for_status()
    paginas = r.json().get('query', {}).get('pages', {}).values()
    for p in sorted(paginas, key=lambda p: p.get('index', 0)):
        info = (p.get('imageinfo') or [{}])[0]
        meta = info.get('extmetadata', {})
        licenca = meta.get('LicenseShortName', {}).get('value', '')
        if info.get('mime') in ('image/jpeg', 'image/png') and licenca.startswith(LIVRES) and info.get('thumburl'):
            yield {'pageid': p['pageid'], 'titulo': p['title'], 'url': info['thumburl'],
                   'pagina': info.get('descriptionurl', ''), 'licenca': licenca,
                   'autor': re.sub('<[^>]+>', '', meta.get('Artist', {}).get('value', ''))}


def degradar(origem: Path, destino: Path):
    img = Image.open(origem).convert('RGB')
    destino.mkdir(parents=True, exist_ok=True)
    img.filter(ImageFilter.GaussianBlur(6)).save(destino / f'{origem.stem}_borrada.jpg')
    ImageEnhance.Brightness(img).enhance(0.25).save(destino / f'{origem.stem}_escura.jpg')


def main(por_classe: int, so: str | None = None):
    contato = os.getenv('COMMONS_CONTATO')
    if not contato:
        sys.exit('Defina antes: $env:COMMONS_CONTATO="seuemail@exemplo.com" (a Wikimedia exige contato).')
    headers = {'User-Agent': f'MeuBairroIA/1.0 (trabalho academico FIAP; {contato}) python-httpx'}
    linhas, vistos, anteriores = [], set(), []
    if so:
        for pasta_antiga in (RAIZ / 'dataset' / so, RAIZ / 'dataset_robustez' / so):
            for f in pasta_antiga.glob('*.jpg'):
                f.unlink()
        if (RAIZ / 'FONTES.csv').exists():
            with open(RAIZ / 'FONTES.csv', encoding='utf-8') as f:
                anteriores = [r for r in csv.DictReader(f) if not r['arquivo'].startswith(f'{so}/')]
    with httpx.Client(headers=headers, timeout=60, follow_redirects=True) as c:
        for classe, termos in ({so: BUSCAS[so]} if so else BUSCAS).items():
            alvo = por_classe + (2 if classe == 'NENHUM' else 0)
            por_termo = -(-alvo // len(termos))
            pasta = RAIZ / 'dataset' / classe
            pasta.mkdir(parents=True, exist_ok=True)
            for termo in termos:
                feitas = 0
                try:
                    itens = list(buscar(c, termo))
                except httpx.HTTPError as e:
                    print(f'  falha na busca "{termo}": {e}')
                    continue
                for item in itens:
                    if feitas >= por_termo or item['pageid'] in vistos:
                        continue
                    try:
                        dados = c.get(item['url']).content
                        arq = pasta / f"{classe.lower()}_{item['pageid']}.jpg"
                        Image.open(io.BytesIO(dados)).convert('RGB').save(arq, quality=90)
                    except Exception as e:
                        print(f'  pulou {item["titulo"]}: {e}')
                        continue
                    vistos.add(item['pageid'])
                    feitas += 1
                    linhas.append({'arquivo': f'{classe}/{arq.name}', **{k: item[k] for k in ('titulo', 'autor', 'licenca', 'pagina')}})
                    if classe != 'NENHUM':
                        degradar(arq, RAIZ / 'dataset_robustez' / classe)
                    time.sleep(1)
            print(f'{classe}: ok')
    if not linhas:
        sys.exit('Nenhuma foto baixada. Veja as mensagens de falha acima.')
    with open(RAIZ / 'FONTES.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['arquivo', 'titulo', 'autor', 'licenca', 'pagina'])
        w.writeheader()
        w.writerows(anteriores + linhas)
    print(f'{len(linhas)} fotos baixadas. Veja eval/FONTES.csv e confira as pastas antes de avaliar.')


if __name__ == '__main__':
    n = int(sys.argv[sys.argv.index('--por-classe') + 1]) if '--por-classe' in sys.argv else 6
    categoria = sys.argv[sys.argv.index('--so') + 1].upper() if '--so' in sys.argv else None
    main(n, categoria)
