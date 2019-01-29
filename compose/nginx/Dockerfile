ARG NGINX_VERSION

FROM nginx:$NGINX_VERSION

COPY nginx.conf /tmp/tpl/nginx.conf

RUN sed 's/{{HOST}}/${HOST}/' /tmp/tpl/nginx.conf > /etc/nginx/nginx.conf
