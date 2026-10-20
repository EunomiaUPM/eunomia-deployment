---
title: Retos
description: Ideas para construir sobre el espacio de datos de la fábrica, de más fácil a más ambicioso.
---

Todos parten del despliegue de la [guía rápida](../getting-started/quickstart.md). La [referencia de la API](../reference/api.md) y la página de [intercambio de datos](../guides/data-exchange.md) tienen las llamadas que necesitas, y `./eunomia e2e -v` enseña cada petición y su respuesta.

## Para calentar

- **Panel de la flota**: una aplicación que pide los robots por el espacio de datos (`./eunomia demo robots` hace lo mismo desde la terminal) y muestra el OEE, la tasa de defectos y el consumo de cada robot por año.
- **Alertas en directo**: un servicio que recibe los eventos push de los robots (tu propio endpoint en el `dataAddress` de la transferencia) y avisa cuando `robot_temperature` o `robot_vibration` pasan de un umbral.

## Un paso más

- **Mantenimiento predictivo**: combina las medidas anuales (MTBF, mantenimientos, horas de parada) con los eventos en directo para estimar qué robot va a fallar antes.
- **Varias fábricas**: levanta varios proveedores con `./eunomia connector add … --role provider`, publica en cada uno el catálogo de la fábrica y construye un consumidor que compare las flotas.
- **Políticas a medida**: crea políticas ODRL nuevas en el catálogo del proveedor (por ejemplo, solo para investigación, o con fecha de caducidad) y comprueba qué ofertas acepta la negociación.

## Para los más ambiciosos

- **Tu propio backend**: sustituye la fábrica por datos tuyos, con sus conectores y su entrada en el catálogo. Ver [extender el despliegue](../guides/extending.md).
- **Tu propia autoridad**: levanta una autoridad con `./eunomia authority add` y monta un segundo espacio de datos con sus propias reglas de admisión.
- **Una interfaz de negociación**: una aplicación que lleve al usuario por catálogo, oferta, contrato y transferencia, enseñando en cada paso el estado DSP.

> **Por completar:** criterios de evaluación y entregables.
