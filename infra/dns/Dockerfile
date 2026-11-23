# Servidor de DNS + DHCP da rede da Vinheria (simula o papel do Windows Server)
FROM alpine:3.20
RUN apk add --no-cache dnsmasq && mkdir -p /var/lib/misc
COPY dnsmasq.conf /etc/dnsmasq.conf
COPY vinheria.hosts /etc/vinheria.hosts
EXPOSE 53/udp 53/tcp 67/udp
CMD ["dnsmasq", "-k", "--conf-file=/etc/dnsmasq.conf"]
