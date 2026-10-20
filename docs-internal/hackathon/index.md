---
title: Hackatón EUNOMIA
description: Construye sobre un espacio de datos de verdad: una fábrica con robots, contratos que se negocian solos y datos que viajan con sus reglas.
---

> **Por completar:** fecha, lugar, formato (presencial u online), premios y enlace de inscripción.

## De qué va

Un **espacio de datos** es una red donde las organizaciones comparten datos sin perder el control: quién los usa, para qué y en qué condiciones. Cada participante demuestra quién es con credenciales verificables, cada intercambio va precedido de un contrato y los datos viajan por el conector del que los ofrece, nunca directamente.

EUNOMIA es el framework que monta todo eso, y en este hackatón lo tienes entero en tu portátil: una **autoridad** que da de alta a los participantes, un **proveedor** que comparte los datos de una **fábrica con robots** y un **consumidor** que los negocia, los descarga y recibe en directo los eventos que emiten los robots.

Tu reto es construir algo encima.

## Por qué participar

- **Tecnología que se está desplegando en Europa**: Dataspace Protocol, credenciales verificables, Gaia-X.
- **Arrancas en minutos**: tres comandos y el espacio de datos funciona, con datos de ejemplo de verdad.
- **Sin cajas negras**: todo es código abierto y cada paso se puede ver, repetir y cambiar.

## Empieza aquí

Solo necesitas Docker. Sigue la [guía rápida](../getting-started/quickstart.md):

```bash
./eunomia doctor
./eunomia up
./eunomia e2e
```

Si `e2e` termina con `END-TO-END TEST PASSED`, ya tienes un espacio de datos funcionando. Mira [qué hay en la fábrica](../concepts/demo-factory.md) y [cómo se mueven los datos](../guides/data-exchange.md).

## Trabajar en equipo

Cada equipo puede tener sus propios participantes, en sus propios puertos, junto al despliegue base:

```bash
./eunomia connector add equipo-azul --role provider --onboard
./eunomia connector add equipo-rojo --onboard
./eunomia gaia --consumer equipo-rojo --provider equipo-azul
```

Todo lo que puedes hacer con ellos está en [participantes adicionales](../guides/instances.md).

## Retos

Ideas para empezar, de más fácil a más ambicioso: [retos](./challenges.md).

## Si algo falla

Primero `./eunomia doctor` y la página de [problemas frecuentes](../troubleshooting.md).

> **Por completar:** canal de soporte durante el evento (Slack, Discord, mesa de ayuda).
