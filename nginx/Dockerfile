FROM nginx:1.27

RUN rm /etc/nginx/conf.d/default.conf
COPY project.conf /etc/nginx/conf.d/
COPY fullchain.pem /etc/ssl/certs/certificate.pem
COPY privkey.pem /etc/ssl/private/key.pem
