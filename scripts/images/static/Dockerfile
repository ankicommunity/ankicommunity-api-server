# vim:set ft=dockerfile
FROM nginx:stable

COPY ./build/static/ /var/www/static
COPY ./images/static/nginx.conf /etc/nginx/conf.d/default.conf
