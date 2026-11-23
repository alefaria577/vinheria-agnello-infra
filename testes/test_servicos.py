"""
Testes automaticos dos dois microsservicos (rodam no pipeline do Jenkins).
Executar: python -m unittest discover -s testes -v
"""
import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("JWT_SEGREDO", "segredo-somente-para-testes-1234567890")
RAIZ = Path(__file__).resolve().parent.parent


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


rastreamento = carregar("rastreamento", RAIZ / "servicos/rastreamento/app.py")
pedidos = carregar("pedidos", RAIZ / "servicos/pedidos/app.py")


class RespostaFalsa:
    """Faz o Pedidos falar com o Rastreamento real, mas sem rede."""
    def __init__(self, r):
        self.status_code, self._json = r.status_code, r.get_json()

    def json(self):
        return self._json


def get_via_rastreamento(url, headers, timeout):
    caminho = url.split(":5001", 1)[1]
    return RespostaFalsa(rastreamento.app.test_client().get(caminho, headers=headers))


class TestRastreamento(unittest.TestCase):
    def setUp(self):
        self.c = rastreamento.app.test_client()

    def test_health_publico(self):
        self.assertEqual(self.c.get("/health").status_code, 200)

    def test_sem_token_401(self):
        self.assertEqual(self.c.get("/lotes").status_code, 401)

    def test_token_de_usuario_nao_serve_para_servico_401(self):
        token = pedidos.gerar_token_usuario("vendedor", "VENDEDOR")  # audiencia errada
        r = self.c.get("/lotes", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(r.status_code, 401)

    def test_token_de_servico_200(self):
        r = self.c.get("/lotes/L2024-01", headers={"Authorization": f"Bearer {pedidos.gerar_token_servico()}"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["status"], "DISPONIVEL")


class TestPedidos(unittest.TestCase):
    def setUp(self):
        self.c = pedidos.app.test_client()
        pedidos.PEDIDOS.clear()

    def login(self, usuario="vendedor", senha="Vinho@2026"):
        return self.c.post("/auth/login", json={"usuario": usuario, "senha": senha})

    def test_login_ok_devolve_token(self):
        r = self.login()
        self.assertEqual(r.status_code, 200)
        self.assertIn("token", r.get_json())

    def test_login_senha_errada_401(self):
        self.assertEqual(self.login(senha="errada").status_code, 401)

    def test_senha_guardada_como_hash(self):
        self.assertNotIn("Vinho@2026", pedidos.USUARIOS["vendedor"]["senha"])

    def test_pedidos_sem_token_401(self):
        self.assertEqual(self.c.get("/pedidos").status_code, 401)

    @mock.patch.object(pedidos.requests, "get", side_effect=get_via_rastreamento)
    def test_pedido_valido_201(self, _):
        token = self.login().get_json()["token"]
        r = self.c.post("/pedidos", json={"lote": "L2024-01", "quantidade": 6},
                        headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(r.status_code, 201)

    @mock.patch.object(pedidos.requests, "get", side_effect=get_via_rastreamento)
    def test_lote_bloqueado_409(self, _):
        token = self.login().get_json()["token"]
        r = self.c.post("/pedidos", json={"lote": "L2023-07", "quantidade": 1},
                        headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(r.status_code, 409)

    @mock.patch.object(pedidos.requests, "get", side_effect=get_via_rastreamento)
    def test_estoque_insuficiente_409(self, _):
        token = self.login().get_json()["token"]
        r = self.c.post("/pedidos", json={"lote": "L2024-02", "quantidade": 50},
                        headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(r.status_code, 409)


if __name__ == "__main__":
    unittest.main(verbosity=2)
