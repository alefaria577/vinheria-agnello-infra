#!/bin/sh
# Script chamado pelo cliente DHCP (udhcpc) da estacao da loja.
# Aplica o IP, o gateway e o DNS que o servidor DHCP enviou.
case "$1" in
  bound|renew)
    ip addr flush dev "$interface"
    ip addr add "$ip/${mask:-24}" dev "$interface"
    [ -n "$router" ] && ip route replace default via "${router%% *}" dev "$interface"
    {
      [ -n "$domain" ] && echo "search $domain"
      for servidor in $dns; do echo "nameserver $servidor"; done
    } > /etc/resolv.conf
    echo "DHCP: IP $ip/$mask | gateway $router | DNS $dns | dominio $domain"
    ;;
esac
exit 0
