import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from . import geracao, visao

LIMIAR = float(os.getenv('LIMIAR_CONFIANCA', '0.50'))
TIPOS = {'image/jpeg', 'image/png', 'image/webp'}
TAMANHO_MAX = 8 * 1024 * 1024

app = FastAPI(title='Meu Bairro IA', version='1.0.0')

AVISO = 'Sugestão gerada por IA. Confira e edite antes de enviar.'


@app.get('/saude')
def saude():
    return {'status': 'ok'}


@app.post('/classificar')
async def classificar(foto: UploadFile = File(...), observacao: str = Form('')):
    if foto.content_type not in TIPOS:
        raise HTTPException(415, 'Envie uma imagem JPEG, PNG ou WebP.')
    dados = await foto.read()  # a foto fica só em memória: nada é gravado em disco
    if len(dados) > TAMANHO_MAX:
        raise HTTPException(413, 'Imagem maior que 8 MB.')
    try:
        visual = visao.classificar(dados)
    except Exception:
        raise HTTPException(422, 'Não foi possível ler a imagem.')

    if visual['categoria'] == 'NENHUM':
        return {'categoriaSugerida': None, 'confianca': visual['confianca'], 'ranking': visual['ranking'],
                'precisaConfirmar': True, 'titulo': None, 'descricao': None, 'urgencia': None,
                'origemTexto': None,
                'aviso': 'Não identificamos um problema urbano na foto. Escolha o tipo manualmente.'}

    texto, origem = geracao.gerar(visual['categoria'], visual['confianca'], observacao)
    return {'categoriaSugerida': visual['categoria'], 'confianca': visual['confianca'],
            'ranking': visual['ranking'], 'precisaConfirmar': visual['confianca'] < LIMIAR,
            **texto, 'origemTexto': origem, 'aviso': AVISO}
