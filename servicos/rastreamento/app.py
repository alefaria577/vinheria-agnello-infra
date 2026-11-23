"""
Vinheria Agnello - Microsservico de Rastreamento de Vinhos
Guarda o estado de cada lote (da uva a venda). Nao fica exposto para fora da rede:
so responde a quem apresenta um token JWT valido emitido para o servico "rastreamento".
"""
import os
from functools import wraps

import jwt
from flask import Flask, jsonify, request

app = Flask(__name__)
SEGREDO = os.environ.get("JWT_SEGREDO", "")
AUDIENCIA = "rastreamento"

# Dados de exemplo (lotes da vinicola)
LOTES = {
    "L2024-01": {"vinho": "Cabernet Sauvignon Reserva", "safra": 2024, "status": "DISPONIVEL", "garrafas": 120},
    "L2024-02": {"vinho": "Merlot Agnello", "safra": 2024, "status": "DISPONIVEL", "garrafas": 8},
    "L2025-01": {"vinho": "Chardonnay Jovem", "safra": 2025, "status": "EM_FERMENTACAO", "garrafas": 0},
    "L2023-07": {"vinho": "Tannat Gran Reserva", "safra": 2023, "status": "BLOQUEADO_QUALIDADE", "garrafas": 60},
}


def exige_token(f):
    """Confere o Bearer token: assinatura, validade (exp) e audiencia."""
    @wraps(f)
    def verificar(*args, **kwargs):
        cabecalho = request.headers.get("Authorization", "")
        if not cabecalho.startswith("Bearer "):
            return jsonify(erro="Token ausente"), 401
        try:
            dados = jwt.decode(cabecalho[7:], SEGREDO, algorithms=["HS256"], audience=AUDIENCIA)
        except jwt.ExpiredSignatureError:
            return jsonify(erro="Token expirado"), 401
        except jwt.InvalidTokenError:
            return jsonify(erro="Token invalido"), 401
        if "lotes:ler" not in dados.get("escopo", ""):
            return jsonify(erro="Sem permissao para ler lotes"), 403
        request.chamador = dados.get("sub")
        return f(*args, **kwargs)
    return verificar


@app.get("/health")
def health():
    return jsonify(servico="rastreamento", status="ok")


@app.get("/lotes")
@exige_token
def listar_lotes():
    return jsonify([{"lote": k, **v} for k, v in LOTES.items()])


@app.get("/lotes/<codigo>")
@exige_token
def consultar_lote(codigo):
    lote = LOTES.get(codigo.upper())
    if not lote:
        return jsonify(erro="Lote nao encontrado"), 404
    app.logger.info("Lote %s consultado por %s", codigo, request.chamador)
    return jsonify(lote=codigo.upper(), **lote)


if __name__ == "__main__":
    if not SEGREDO:
        raise SystemExit("Defina a variavel de ambiente JWT_SEGREDO")
    app.run(host="0.0.0.0", port=5001)
