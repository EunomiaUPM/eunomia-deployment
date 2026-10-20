# Imagen mínima para ejecutar los scripts de onboarding de main (scripts/*.sh)
# igual en Windows, Linux y macOS, sin pedir bash/curl/jq en el equipo.
# La construye hack.sh / hack.ps1 con el contexto en la raíz del repo
# (tools.Dockerfile.dockerignore deja pasar solo los .sh necesarios):
#   docker build -f deployment/hack/tools.Dockerfile -t eunomia-hack-tools:local .
FROM alpine:3.20
RUN apk add --no-cache bash curl jq
COPY scripts/*.sh deployment/hack/tools/*.sh /scripts/
# Los checkouts de Windows traen CRLF; bash dentro del contenedor necesita LF.
RUN sed -i 's/\r$//' /scripts/*.sh
WORKDIR /scripts
