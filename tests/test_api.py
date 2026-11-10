import io

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import geracao, main, visao

cliente = TestClient(main.app)


def imagem_bytes(formato='JPEG') -> bytes:
    buf = io.BytesIO()
    Image.new('RGB', (64, 64), (120, 120, 120)).save(buf, formato)
    return buf.getvalue()


def enviar(conteudo: bytes, tipo='image/jpeg'):
    return cliente.post('/classificar', files={'foto': ('f.jpg', conteudo, tipo)}, data={'observacao': ''})


def falso_visual(categoria, confianca):
    return lambda _dados: {'categoria': categoria, 'confianca': confianca,
                           'ranking': [{'categoria': categoria, 'confianca': confianca}]}


def test_tipo_de_arquivo_invalido():
    assert enviar(b'texto', 'text/plain').status_code == 415


def test_imagem_corrompida():
    assert enviar(b'nao sou imagem').status_code == 422


def test_arquivo_grande_demais(monkeypatch):
    monkeypatch.setattr(main, 'TAMANHO_MAX', 10)
    assert enviar(imagem_bytes()).status_code == 413


def test_foto_sem_problema_pede_escolha_manual(monkeypatch):
    monkeypatch.setattr(visao, 'classificar', falso_visual('NENHUM', 0.8))
    r = enviar(imagem_bytes()).json()
    assert r['categoriaSugerida'] is None and r['precisaConfirmar'] is True


def test_sucesso_com_llm(monkeypatch):
    monkeypatch.setattr(visao, 'classificar', falso_visual('BURACO', 0.9))
    monkeypatch.setattr(geracao, 'gerar', lambda *a: ({'titulo': 'Buraco', 'descricao': 'Buraco na via.', 'urgencia': 'ALTA'}, 'llm'))
    r = enviar(imagem_bytes()).json()
    assert r['categoriaSugerida'] == 'BURACO' and r['precisaConfirmar'] is False and r['urgencia'] == 'ALTA'


def test_baixa_confianca_pede_confirmacao(monkeypatch):
    monkeypatch.setattr(visao, 'classificar', falso_visual('LIXO', 0.3))
    monkeypatch.setattr(geracao, 'gerar', lambda *a: (geracao.padrao('LIXO'), 'modelo-padrao'))
    assert enviar(imagem_bytes()).json()['precisaConfirmar'] is True


def test_llm_offline_usa_texto_padrao(monkeypatch):
    def cai(*a, **k):
        raise httpx.ConnectError('offline')

    monkeypatch.setattr(geracao.httpx, 'post', cai)
    dados, origem = geracao.gerar('BURACO', 0.9)
    assert origem == 'modelo-padrao' and dados['urgencia'] == 'MEDIA'


@pytest.mark.parametrize('resposta', ['isso nao e json', '{"titulo": "", "descricao": ""}'])
def test_llm_resposta_invalida_usa_texto_padrao(monkeypatch, resposta):
    class Falsa:
        def raise_for_status(self): pass
        def json(self): return {'response': resposta}

    monkeypatch.setattr(geracao.httpx, 'post', lambda *a, **k: Falsa())
    assert geracao.gerar('LIXO', 0.7)[1] == 'modelo-padrao'
