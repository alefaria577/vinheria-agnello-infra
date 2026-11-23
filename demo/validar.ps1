# Valida todo o ambiente da Vinheria Agnello (Sprint 7) de uma vez.
# Rodar na pasta vinheria-sprint7:   powershell -ExecutionPolicy Bypass -File demo\validar.ps1
$script:ok = 0; $script:falhas = 0
function Teste($nome, $condicao, $detalhe) {
    if ($condicao) { Write-Host "[OK]    $nome" -ForegroundColor Green; $script:ok++ }
    else { Write-Host "[FALHA] $nome" -ForegroundColor Red; if ($detalhe) { Write-Host "        $detalhe" -ForegroundColor DarkYellow }; $script:falhas++ }
}
function Codigo($argumentos) { return (& curl.exe -s -k -o NUL -w "%{http_code}" @argumentos) }

Write-Host "`n=== 1. Conteineres ===" -ForegroundColor Cyan
$nomes = docker ps --format "{{.Names}}"
foreach ($c in "vinheria-dns","vinheria-rastreamento","vinheria-pedidos","vinheria-www","vinheria-gateway","vinheria-jenkins","vinheria-estacao") {
    Teste "$c no ar" ($nomes -contains $c) "Rode: docker compose up -d --build   e veja: docker logs $c"
}

Write-Host "`n=== 2. DHCP ===" -ForegroundColor Cyan
$ip = (docker exec vinheria-estacao ip -4 -o addr show eth0 2>&1) | Out-String
Teste "Estacao recebeu IP do DHCP (172.28.0.100 a .150)" ($ip -match "172\.28\.0\.(1[0-4][0-9]|150)/") $ip.Trim()
$lease = (docker exec vinheria-dns cat /var/lib/misc/dnsmasq.leases 2>&1) | Out-String
Teste "Concessao registrada no servidor DHCP" ($lease -match "estacao-loja") $lease.Trim()

Write-Host "`n=== 3. DNS ===" -ForegroundColor Cyan
$ns = (docker exec vinheria-estacao nslookup pedidos.vinheria.local 2>&1) | Out-String
Teste "DNS resolve pedidos.vinheria.local -> 172.28.0.11" ($ns -match "172\.28\.0\.11") $ns.Trim()
$ns = (docker exec vinheria-estacao nslookup rastreamento.vinheria.local 2>&1) | Out-String
Teste "DNS resolve rastreamento.vinheria.local -> 172.28.0.10" ($ns -match "172\.28\.0\.10") $ns.Trim()
$ns = (docker exec vinheria-estacao nslookup estacao-loja.vinheria.local 2>&1) | Out-String
Teste "DNS registrou a estacao que veio do DHCP" ($ns -match "172\.28\.0\.1[0-5][0-9]") $ns.Trim()

Write-Host "`n=== 4. Comunicacao entre servicos ===" -ForegroundColor Cyan
$h = (docker exec vinheria-estacao wget -qO- http://pedidos.vinheria.local:5002/health 2>&1) | Out-String
Teste "Estacao acessa o Pedidos pelo nome" ($h -match "ok") $h.Trim()
$r = (docker exec vinheria-estacao sh -c "wget -S -O /dev/null http://rastreamento.vinheria.local:5001/lotes 2>&1") | Out-String
Teste "Rastreamento recusa acesso sem token (401)" ($r -match "401") $r.Trim()

Write-Host "`n=== 5. API, JWT e HTTPS ===" -ForegroundColor Cyan
Teste "Pedidos por HTTP (porta 8081) no ar" ((Codigo @("http://localhost:8081/health")) -eq "200")
Teste "Pedidos por HTTPS (porta 8443) no ar" ((Codigo @("https://localhost:8443/health")) -eq "200") "Se falhar: docker compose restart gateway"
Teste "Login com senha errada -> 401" ((Codigo @("-X","POST","https://localhost:8443/auth/login","-H","Content-Type: application/json","--data","@demo/login-errado.json")) -eq "401")
$login = (& curl.exe -s -k -X POST https://localhost:8443/auth/login -H "Content-Type: application/json" --data "@demo/login.json") | ConvertFrom-Json
Teste "Login correto devolve token JWT" ($login.token) "Resposta: $login"
$aut = "Authorization: Bearer $($login.token)"
Teste "Listar pedidos sem token -> 401" ((Codigo @("https://localhost:8443/pedidos")) -eq "401")
Teste "Pedido valido (Pedidos consulta o Rastreamento com JWT) -> 201" ((Codigo @("-X","POST","https://localhost:8443/pedidos","-H",$aut,"-H","Content-Type: application/json","--data","@demo/pedido.json")) -eq "201")
Teste "Pedido de lote bloqueado pela qualidade -> 409" ((Codigo @("-X","POST","https://localhost:8443/pedidos","-H",$aut,"-H","Content-Type: application/json","--data","@demo/pedido-bloqueado.json")) -eq "409")

Write-Host "`n=== 6. Jenkins e publicacao ===" -ForegroundColor Cyan
Teste "Jenkins no ar (porta 8080)" ((Codigo @("http://localhost:8080/login")) -eq "200") "O Jenkins leva 1 a 2 minutos para iniciar"
Teste "Servidor de publicacao no ar (porta 8088)" ((Codigo @("http://localhost:8088")) -eq "200")

Write-Host "`n=== 7. Testes automaticos (11 testes) ===" -ForegroundColor Cyan
docker run --rm -v "${PWD}:/app" -w /app python:3.12-slim sh -c "pip install -q --root-user-action=ignore flask==3.0.3 pyjwt==2.9.0 requests==2.32.3 >/dev/null 2>&1 && python -m unittest discover -s testes" 2>&1 | Select-Object -Last 3
Teste "Testes unitarios passaram" ($LASTEXITCODE -eq 0)

Write-Host "`n=== Resultado: $($script:ok) OK, $($script:falhas) falha(s) ===" -ForegroundColor $(if ($script:falhas -eq 0) { "Green" } else { "Red" })
