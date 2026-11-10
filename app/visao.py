"""Etapa 1 — Visão computacional: classificação zero-shot da foto com CLIP (pré-treinado, local)."""
import io
import os
from functools import lru_cache

from PIL import Image, ImageOps

MODELO = os.getenv('CLIP_MODEL', 'openai/clip-vit-base-patch32')

# CLIP entende melhor descrições em inglês; cada categoria tem mais de um prompt.
CLASSES = {
    'BURACO': ['a photo of a pothole in a road', 'a photo of damaged asphalt with a hole'],
    'ILUMINACAO': ['a photo of a broken street light', 'a photo of a fallen or leaning utility pole'],
    'LIXO': ['a photo of garbage piled on a street', 'a photo of illegal trash dumping'],
    'ALAGAMENTO': ['a photo of a flooded street', 'a photo of water covering a road'],
    'CALCADA': ['a photo of a broken sidewalk', 'a photo of cracked pavement for pedestrians'],
    'NENHUM': [
        'a photo of a normal clean street',
        'a photo of a person or a room indoors',
        'a blurry or very dark photo',
    ],
}
PROMPTS = [(c, p) for c, ps in CLASSES.items() for p in ps]


@lru_cache(maxsize=1)
def _carregar():
    from transformers import CLIPModel, CLIPProcessor

    return CLIPModel.from_pretrained(MODELO).eval(), CLIPProcessor.from_pretrained(MODELO)


def preparar(dados: bytes) -> Image.Image:
    """Abre a imagem em memória, corrige a rotação e descarta o EXIF (inclui GPS)."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(dados))).convert('RGB')
    img.thumbnail((1024, 1024))
    return img


def classificar(dados: bytes) -> dict:
    import torch

    img = preparar(dados)
    modelo, proc = _carregar()
    entrada = proc(text=[p for _, p in PROMPTS], images=img, return_tensors='pt', padding=True)
    with torch.no_grad():
        probs = modelo(**entrada).logits_per_image.softmax(dim=1)[0].tolist()
    pontos: dict[str, float] = {}
    for (classe, _), p in zip(PROMPTS, probs):
        pontos[classe] = pontos.get(classe, 0.0) + p
    ranking = sorted(pontos.items(), key=lambda x: -x[1])
    return {
        'categoria': ranking[0][0],
        'confianca': round(ranking[0][1], 3),
        'ranking': [{'categoria': c, 'confianca': round(p, 3)} for c, p in ranking[:3]],
    }
