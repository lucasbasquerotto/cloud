ARG NGINX_VERSION

FROM nginx:$NGINX_VERSION

ARG WP_HOST
ARG WP_PORT
ARG PMA_HOST
ARG PMA_PORT

COPY nginx.conf /tmp/tpl/nginx.conf

RUN sed 's/{{HOST}}/${HOST}/' /tmp/tpl/nginx.conf > /etc/nginx/nginx.conf
