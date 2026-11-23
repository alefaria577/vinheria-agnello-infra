"""
Vinheria Agnello - Microsservico de Gestao de Pedidos (Sprint 6 -> Sprint 7)
- POST /auth/login: usuario e senha -> token JWT (senha guardada como hash)
- GET/POST /pedidos: exigem o token do usuario
- Antes de registrar um pedido, consulta o lote no microsservico de Rastreamento
  pelo nome DNS (rastreamento.vinheria.local), enviando um token JWT de servico.
"""
import datetime as dt
import os
from functools import wraps

import jwt
import requests
from flask import Flask, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
SEGREDO = os.environ.get("JWT_SEGREDO", "")
RASTREAMENTO_URL = os.environ.get("RASTREAMENTO_URL", "http://rastreamento.vinheria.local:5001")
AUDIENCIA_USUARIOS = "pedidos"

# Usuarios de exemplo: a senha nunca fica em texto puro, so o hash
USUARIOS = {
    "vendedor": {"senha": generate_password_hash("Vinho@2026"), "papel": "VENDEDOR"},
    "gerente": {"senha": generate_password_hash("Agnello@2026"), "papel": "GERENTE"},
}
PEDIDOS = []


def agora():
    return dt.datetime.now(dt.timezone.utc)


def gerar_token_usuario(usuario, papel):
    return jwt.encode({"sub": usuario, "papel": papel, "aud": AUDIENCIA_USUARIOS,
                       "iat": agora(), "exp": agora() + dt.timedelta(minutes=30)}, SEGREDO, algorithm="HS256")


def gerar_token_servico():
    """Token curto (2 min) que identifica o servico Pedidos perante o Rastreamento."""
    return jwt.encode({"sub": "svc-pedidos", "aud": "rastreamento", "escopo": "lotes:ler",
                       "iat": agora(), "exp": agora() + dt.timedelta(minutes=2)}, SEGREDO, algorithm="HS256")


def exige_login(*papeis):
    def decorador(f):
        @wraps(f)
        def verificar(*args, **kwargs):
            cabecalho = request.headers.get("Authorization", "")
            if not cabecalho.startswith("Bearer "):
                return jsonify(erro="Faca login: token ausente"), 401
            try:
                dados = jwt.decode(cabecalho[7:], SEGREDO, algorithms=["HS256"], audience=AUDIENCIA_USUARIOS)
            except jwt.InvalidTokenError:
                return jsonify(erro="Token invalido ou expirado"), 401
            if papeis and dados.get("papel") not in papeis:
                return jsonify(erro="Seu perfil nao pode fazer esta acao"), 403
            request.usuario = dados["sub"]
            return f(*args, **kwargs)
        return verificar
    return decorador


def consultar_lote(codigo):
    """Chamada REST servico -> servico com JWT. Retorna (status_http, json)."""
    resposta = requests.get(f"{RASTREAMENTO_URL}/lotes/{codigo}",
                            headers={"Authorization": f"Bearer {gerar_token_servico()}"}, timeout=5)
    return resposta.status_code, resposta.json()


@app.get("/health")
def health():
    return jsonify(servico="pedidos", status="ok")


@app.post("/auth/login")
def login():
    corpo = request.get_json(silent=True) or {}
    usuario, senha = str(corpo.get("usuario", "")), str(corpo.get("senha", ""))
    conta = USUARIOS.get(usuario)
    if not conta or not check_password_hash(conta["senha"], senha):
        return jsonify(erro="Usuario ou senha invalidos"), 401
    return jsonify(token=gerar_token_usuario(usuario, conta["papel"]), papel=conta["papel"], expira_em_min=30)


@app.get("/pedidos")
@exige_login()
def listar_pedidos():
    return jsonify(PEDIDOS)


@app.post("/pedidos")
@exige_login("VENDEDOR", "GERENTE")
def criar_pedido():
    corpo = request.get_json(silent=True) or {}
    codigo = str(corpo.get("lote", "")).strip().upper()
    quantidade = corpo.get("quantidade")
    if not codigo or not isinstance(quantidade, int) or quantidade <= 0:
        return jsonify(erro="Informe lote e quantidade (inteiro maior que zero)"), 400
    try:
        status, lote = consultar_lote(codigo)
    except requests.RequestException:
        return jsonify(erro="Rastreamento indisponivel, tente novamente"), 503
    if status == 404:
        return jsonify(erro="Lote nao encontrado"), 404
    if status != 200:
        return jsonify(erro="Falha ao consultar o lote", detalhe=lote), 502
    if lote["status"] != "DISPONIVEL":
        return jsonify(erro=f"Lote {codigo} nao esta disponivel ({lote['status']})"), 409
    if lote["garrafas"] < quantidade:
        return jsonify(erro=f"Estoque insuficiente: {lote['garrafas']} garrafas"), 409
    pedido = {"id": len(PEDIDOS) + 1, "lote": codigo, "vinho": lote["vinho"], "quantidade": quantidade,
              "vendedor": request.usuario, "criado_em": agora().isoformat(timespec="seconds")}
    PEDIDOS.append(pedido)
    return jsonify(pedido), 201


if __name__ == "__main__":
    if not SEGREDO:
        raise SystemExit("Defina a variavel de ambiente JWT_SEGREDO")
    app.run(host="0.0.0.0", port=5002)
