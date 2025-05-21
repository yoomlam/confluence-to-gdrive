FROM nginx:1.27

RUN rm /etc/nginx/conf.d/default.conf
COPY project.conf /etc/nginx/conf.d/

# SSL certificates
COPY fullchain.pem /etc/ssl/certs/certificate.pem
COPY privkey.pem /etc/ssl/private/key.pem

# Basic authentication
COPY htpasswd /etc/nginx/.htpasswd

COPY html/* /usr/share/nginx/html/
