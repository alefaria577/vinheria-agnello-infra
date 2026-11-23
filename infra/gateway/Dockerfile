# Gateway HTTPS: recebe o trafego criptografado (TLS) e repassa ao microsservico de Pedidos.
# O certificado de laboratorio e gerado na construcao da imagem: a chave privada nunca vai para o Git.
FROM nginx:1.27-alpine
RUN apk add --no-cache openssl && mkdir -p /etc/nginx/tls && \
    openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
      -subj "/CN=gateway.vinheria.local/O=Vinheria Agnello" \
      -addext "subjectAltName=DNS:gateway.vinheria.local,DNS:localhost" \
      -keyout /etc/nginx/tls/vinheria.key -out /etc/nginx/tls/vinheria.crt
COPY nginx.conf /etc/nginx/conf.d/default.conf
