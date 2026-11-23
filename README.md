# Vinheria Agnello · Infraestrutura e deploy dos microsserviços

Ambiente completo, em contêineres Docker, com dois microsserviços da Vinheria Agnello: uma rede própria com **DHCP e DNS**, **deploy automático com Jenkins** e **comunicação segura** (login com JWT e HTTPS).

**O que este projeto demonstra**
-  **Rede e serviços:** rede isolada `172.28.0.0/24`, servidor DHCP + DNS (dnsmasq) e serviços que se encontram pelo nome (`*.vinheria.local`).
- **DevOps:** pipeline no Jenkins que busca o código neste repositório, testa, verifica segredos e publica numa pasta que simula o IIS.
-  **Segurança:** login com token JWT, token próprio entre serviços, HTTPS com TLS 1.3 e comparação HTTP x HTTPS no Wireshark.

---

## Arquitetura

```mermaid
flowchart LR
    U([Navegador / curl]) -- "HTTPS :8443" --> GW[gateway<br/>nginx + TLS]
    U -. "HTTP :8081<br/>só para comparação" .-> PED
    GW --> PED[pedidos<br/>Gestão de Pedidos]
    PED -- "JWT de serviço" --> RAS[rastreamento<br/>Rastreamento de Vinhos]
    U -- ":8080" --> JEN[jenkins]
    JEN -- "deploy" --> PUB[(pasta publicacao)]
    U -- ":8088" --> WWW[www<br/>simula o IIS]
    WWW --- PUB
    EST[estacao-loja] -- "pede IP" --> DNS[dns<br/>DHCP + DNS]
    PED & RAS & GW & EST -. "resolvem nomes" .-> DNS
```

| Contêiner | Nome no DNS | IP | Função |
|---|---|---|---|
| `vinheria-dns` | dns.vinheria.local | 172.28.0.2 | Servidor **DNS + DHCP** (dnsmasq) |
| `vinheria-rastreamento` | rastreamento.vinheria.local | 172.28.0.10 | Microsserviço **Rastreamento de Vinhos** (só rede interna) |
| `vinheria-pedidos` | pedidos.vinheria.local | 172.28.0.11 | Microsserviço **Gestão de Pedidos** (login JWT) |
| `vinheria-www` | www.vinheria.local | 172.28.0.12 | Servidor de **publicação** (simula o IIS) |
| `vinheria-gateway` | gateway.vinheria.local | 172.28.0.13 | **HTTPS (TLS)** na frente do Pedidos |
| `vinheria-jenkins` | jenkins.vinheria.local | 172.28.0.14 | **Jenkins** (pipeline de deploy) |
| `vinheria-estacao` | estacao-loja.vinheria.local | DHCP (.100 a .150) | Estação da loja que recebe IP por **DHCP** |

**Tecnologias:** Docker Compose · Python 3.12 + Flask · PyJWT · dnsmasq · nginx · Jenkins · Wireshark

---

## Pré-requisitos

- Windows 10/11 com **Docker Desktop** instalado e aberto (ícone da baleia "Engine running").
- **Git**.
- Portas livres: **8080, 8081, 8088 e 8443**.
- Opcional: **Wireshark** (com Npcap) para a comparação HTTP x HTTPS.

---

## ▶️ Como rodar

Abra o **PowerShell** e execute:

**1. Baixe o projeto**
```powershell
git clone https://github.com/alefaria577/vinheria-agnello-infra.git
cd vinheria-agnello-infra
```

**2. Crie o arquivo de configuração**
```powershell
copy .env.example .env
notepad .env
```
Troque os dois valores e salve:

| Variável | Para que serve |
|---|---|
| `JWT_SEGREDO` | Chave que assina os tokens (use 32 caracteres ou mais) |
| `JENKINS_ADMIN_SENHA` | Senha do usuário `admin` do Jenkins |

> O `.env` fica só na sua máquina e não vai para o Git.

**3. Suba o ambiente**
```powershell
docker compose up -d --build
```
Na primeira vez leva alguns minutos (download das imagens). Confira com `docker compose ps`: os contêineres devem aparecer como **Up**. O Jenkins leva cerca de 1 minuto para abrir.

**4. Valide tudo de uma vez**
```powershell
powershell -ExecutionPolicy Bypass -File demo\validar.ps1
```
O script confere contêineres, DHCP, DNS, comunicação entre serviços, JWT, HTTPS, Jenkins e os testes automáticos.
Resultado esperado: **`=== Resultado: 24 OK, 0 falha(s) ===`**

### Endereços

| O quê | Endereço |
|---|---|
| Jenkins | http://localhost:8080 (usuário `admin`, senha do `.env`) |
| Página publicada pelo deploy | http://localhost:8088 |
| API Pedidos por HTTPS | https://localhost:8443/health (certificado de laboratório: aceite o aviso) |
| API Pedidos por HTTP (só para a comparação no Wireshark) | http://localhost:8081/health |

---

## DHCP e DNS

```powershell
docker logs vinheria-estacao                                     # IP, gateway e DNS recebidos por DHCP
docker exec vinheria-dns cat /var/lib/misc/dnsmasq.leases        # concessões do DHCP
docker exec vinheria-estacao nslookup pedidos.vinheria.local     # nome de um serviço -> IP
docker exec vinheria-estacao nslookup estacao-loja.vinheria.local  # a estação registrada no DNS pelo DHCP
docker exec vinheria-estacao wget -qO- http://pedidos.vinheria.local:5002/health
docker logs vinheria-dns                                         # consultas DNS e pedidos DHCP registrados
```

---

## Usando a API

Usuários de exemplo: `vendedor` / `Vinho@2026` e `gerente` / `Agnello@2026`.

```powershell
# 1. Login (devolve um token JWT válido por 30 minutos)
$token = (curl.exe -s -k -X POST https://localhost:8443/auth/login -H "Content-Type: application/json" --data "@demo/login.json" | ConvertFrom-Json).token

# 2. Registrar uma venda (o Pedidos consulta o Rastreamento antes)
curl.exe -k -X POST https://localhost:8443/pedidos -H "Authorization: Bearer $token" -H "Content-Type: application/json" --data "@demo/pedido.json"

# 3. Venda de um lote bloqueado pela qualidade
curl.exe -k -X POST https://localhost:8443/pedidos -H "Authorization: Bearer $token" -H "Content-Type: application/json" --data "@demo/pedido-bloqueado.json"

# 4. Login com senha errada
curl.exe -k -X POST https://localhost:8443/auth/login -H "Content-Type: application/json" --data "@demo/login-errado.json"
```

| Rota (Pedidos) | Acesso | Resposta |
|---|---|---|
| `POST /auth/login` | aberto | token JWT (ou **401** com senha errada) |
| `GET /pedidos` | com token | lista de vendas |
| `POST /pedidos` | com token | **201** registrada · **409** lote bloqueado ou sem estoque · **404** lote inexistente · **503** Rastreamento fora do ar |
| `GET /health` | aberto | situação do serviço |

O **Rastreamento** não tem porta aberta para fora: só o Pedidos chega nele, com um token de serviço que vale 2 minutos.

---

## Pipeline no Jenkins

1. Acesse http://localhost:8080 e entre com `admin` e a senha do `.env`.
2. **Nova tarefa** → nome `vinheria-deploy` → **Pipeline** → **OK**.
3. Em **Pipeline**, escolha **Pipeline script from SCM** e preencha:
   - **SCM:** Git
   - **Repository URL:** `https://github.com/alefaria577/vinheria-agnello-infra.git`
   - **Branch:** `*/main`
   - **Script Path:** `Jenkinsfile`
4. **Salvar** → **Construir agora**.

| Etapa | O que faz |
|---|---|
| Checkout | Baixa a versão mais recente do repositório no GitHub |
| Build | Mostra `Deploy da Vinheria`, instala as dependências e compila os serviços |
| Testes | Roda os 11 testes automáticos |
| Segurança | Confere se não há `.env` nem chave privada no repositório |
| Deploy | Copia os serviços para `publicacao/releases/build-N` e atualiza a página |

Ao terminar, http://localhost:8088 mostra o número do build, o commit e a data do deploy.

---

## HTTP x HTTPS no Wireshark

1. Abra o Wireshark e escolha o adaptador **Adapter for loopback traffic capture**.
2. Filtro `tcp.port == 8081` e faça o login por HTTP:
   ```powershell
   curl.exe -X POST http://localhost:8081/auth/login -H "Content-Type: application/json" --data "@demo/login.json"
   ```
   ➜ usuário, senha e token aparecem em texto puro.
3. Filtro `tcp.port == 8443` e faça o mesmo login por HTTPS (comando do passo 1 de "Usando a API").
   ➜ aparece o handshake **TLS 1.3** e só *Application Data* criptografado.

**Medidas de segurança aplicadas:** senhas guardadas com hash · tokens com prazo curto e destino definido (`aud`) · Rastreamento sem porta exposta · HTTPS com TLS 1.2/1.3 e HSTS · segredos só no `.env` · contêineres sem usuário root · pipeline que bloqueia segredos no código.

---

## Testes automáticos

Já rodam no `validar.ps1` e no pipeline. Para rodar sozinho, sem instalar Python:
```powershell
docker run --rm -v "${PWD}:/app" -w /app python:3.12-slim sh -c "pip install -q flask==3.0.3 pyjwt==2.9.0 requests==2.32.3 && python -m unittest discover -s testes -v"
```

---

## 📁 Estrutura

```
servicos/        rastreamento/ e pedidos/ (código + Dockerfile de cada serviço)
infra/           dns/ (DHCP + DNS), estacao/, gateway/ (HTTPS), jenkins/, web/ (modelo da página)
testes/          11 testes automáticos
demo/            exemplos de requisição e validar.ps1
publicacao/      pasta de publicação (simula o IIS)
Jenkinsfile      pipeline de deploy
docker-compose.yml
```

---

## Parar o ambiente

```powershell
docker compose down        # para tudo
docker compose down -v     # para tudo e apaga os dados do Jenkins (começa do zero)
```

##  Problemas comuns

| Sintoma | Solução |
|---|---|
| `Defina JWT_SEGREDO no arquivo .env` | O `.env` não foi criado: refaça o passo 2 |
| `error during connect` / Docker não responde | Abra o Docker Desktop e espere "Engine running" |
| `port is already allocated` | Outro programa usa a porta 8080, 8081, 8088 ou 8443: feche-o e rode `docker compose up -d` de novo |
| Jenkins não abre | Aguarde cerca de 1 minuto após subir e atualize a página |
| Aviso de certificado no navegador | Esperado: o certificado é de laboratório. Clique em *Avançado* → *Continuar* |
