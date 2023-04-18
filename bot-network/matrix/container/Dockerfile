FROM ubuntu:22.04

ARG TZ=utc
ENV DEBIAN_FRONTEND=noninteractive

RUN mkdir -p /assistant-dev /var/www/web

WORKDIR /assistant-dev

COPY ./container/install-deps.sh /assistant-dev/install-deps.sh
RUN bash /assistant-dev/install-deps.sh && rm -f /assistant-dev/install-deps.sh

ENTRYPOINT [ "bash" ]
