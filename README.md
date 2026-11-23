# Vinheria Agnello · Infraestrutura e deploy dos microsserviços

Parte da arquitetura da Vinheria Agnello rodando em contêineres Docker:

| Contêiner | Nome no DNS | IP | Função |
|---|---|---|---|
| `vinheria-dns` | dns.vinheria.local | 172.28.0.2 | Servidor **DNS + DHCP** (dnsmasq) |
| `vinheria-rastreamento` | rastreamento.vinheria.local | 172.28.0.10 | Microsserviço **Rastreamento de Vinhos** (só rede interna) |
| `vinheria-pedidos` | pedidos.vinheria.local | 172.28.0.11 | Microsserviço **Gestão de Pedidos** (login JWT) |
| `vinheria-www` | www.vinheria.local | 172.28.0.12 | Servidor de **publicação** (simula o IIS) |
| `vinheria-gateway` | gateway.vinheria.local | 172.28.0.13 | **HTTPS (TLS)** na frente do Pedidos |
| `vinheria-jenkins` | jenkins.vinheria.local | 172.28.0.14 | **Jenkins** (pipeline de deploy) |
| `vinheria-estacao` | estacao-loja.vinheria.local | DHCP (.100 a .150) | Estação da loja que recebe IP por **DHCP** |

## Como rodar (Windows + Docker Desktop)

1. Copie `.env.example` para `.env` e troque os valores.
2. No PowerShell, dentro desta pasta:
   ```
   git init -b main
   git add .
   git commit -m "Vinheria Agnello - infraestrutura e microsservicos"
   docker compose up -d --build
   ```
3. Endereços no navegador:
   - Jenkins: http://localhost:8080 (usuário `admin`, senha do `.env`)
   - Publicação: http://localhost:8088
   - Pedidos por HTTP (só para a demonstração): http://localhost:8081/health
   - Pedidos por HTTPS: https://localhost:8443/health (certificado de laboratório: aceite o aviso)

## Testes rápidos

```
docker logs vinheria-estacao                                   # IP recebido por DHCP
docker exec vinheria-dns cat /var/lib/misc/dnsmasq.leases      # concessões do DHCP
docker exec vinheria-estacao nslookup pedidos.vinheria.local   # resolução pelo DNS
docker exec vinheria-estacao nslookup estacao-loja.vinheria.local
docker exec vinheria-estacao wget -qO- http://pedidos.vinheria.local:5002/health
docker logs vinheria-dns                                       # consultas DNS e DHCP registradas

curl.exe -X POST http://localhost:8081/auth/login -H "Content-Type: application/json" --data "@demo/login.json"
curl.exe -k -X POST https://localhost:8443/auth/login -H "Content-Type: application/json" --data "@demo/login.json"
```

Usuários de exemplo: `vendedor` / `Vinho@2026` e `gerente` / `Agnello@2026`.

## Pipeline do Jenkins

Novo Item → **Pipeline** → *Pipeline script from SCM* → Git → Repository URL `/repo` → Branch `*/main` → Script Path `Jenkinsfile`.
Estágios: **Checkout → Build → Testes → Segurança → Deploy** (copia para `publicacao/releases/build-N`).

## Testes automáticos

```
python -m unittest discover -s testes -v
```
