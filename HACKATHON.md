# EUNOMIA: guía rápida para el hackatón

## Requisitos
- **Docker Desktop** (Windows/macOS) o **Docker Engine** (Linux), arrancado.
- **Docker Compose v2** (`docker compose version`).
- Nada más: el onboarding corre dentro de un contenedor (no hace falta bash, curl ni jq en tu equipo).

| Sistema | Comando |
|---|---|
| Linux / macOS | `./hack.sh <comando>` (si da "Permission denied": `chmod +x hack.sh` o `bash hack.sh`) |
| Windows | `.\hack.cmd <comando>` (o `.\hack.ps1 <comando>` si tu ExecutionPolicy lo permite) |

Los dos aceptan los mismos comandos. Ayuda completa: `./hack.sh help`. Puedes comprobar los requisitos con `./hack.sh check`.

Las versiones de las imágenes se cambian en un solo sitio: [`versions.env`](versions.env).

## 1. Mini base (autoridad + provider + consumer)
```bash
./hack.sh base up        # levanta todo y espera a que esté sano
./hack.sh base onboard   # registra provider y consumer en la autoridad y los conecta
./hack.sh base status    # estado y URLs
./hack.sh base stop      # lo para (conserva datos)
./hack.sh base reset     # lo borra todo, volúmenes incluidos, y empieza de cero
```

| Entidad | URL | Usuario |
|---|---|---|
| Autoridad (Heimdall) | http://localhost:1500/admin/home | – |
| Provider | http://localhost:1200/admin/login | `eunomia` / `eunomia` |
| Consumer | http://localhost:1100/admin/login | `eunomia` / `eunomia` |

Postgres: consumer `localhost:1300`, provider `localhost:1400`, heimdall `localhost:1450` (usuario = contraseña = BD = `mini_consumer`, `mini_provider` o `mini_heimdall`).
Los DID son `did:web:host.docker.internal%3A<puerto>`. Desde un contenedor, cada entidad está en `http://host.docker.internal:<puerto>`.

## 2. Añadir un conector o una autoridad
Cada instancia busca puertos libres (HTTP en 1600-1999, Postgres en 15400-15999), tiene su propio proyecto de compose (`hack-<nombre>`) y sus propios contenedores y volúmenes. Su configuración se genera en `instances/<nombre>/`.
```bash
./hack.sh connector add                          # consumer con nombre automático (conn-xxxx)
./hack.sh connector add mi-prov --role provider  # provider llamado mi-prov
./hack.sh connector add mi-con --onboard         # y además lo registra en la autoridad del mini base
./hack.sh authority add mi-aut                   # Heimdall nuevo (--role eco|dataspace)

./hack.sh onboard mi-con --authority mi-aut      # registra un conector en otra autoridad
./hack.sh gaia --consumer mi-con --provider mi-prov --authority authority
                                                 # VCs Gaia-X del consumer + conexión con el provider
./hack.sh connect mi-con mi-prov                 # solo la conexión (si el consumer ya tiene sus VCs)
```
Para referirte a las entidades del mini base usa los nombres `consumer`, `provider` y `authority`, por ejemplo `./hack.sh gaia --consumer mi-con`.

> **Importante**: los providers (el del mini y los creados con `--role provider`) solo aceptan consumers con la credencial `gx:LabelCredential`. Para conseguirla, usa `gaia` con una autoridad `eco` (la del mini base lo es). `connect` a secas se queda en "Pending" si al consumer le falta esa credencial, y el script te lo dirá.

Cada paso comprueba su resultado: la credencial debe quedar en `Finalized` y la conexión en `Approved`. Si no, el comando falla con un mensaje.

## 3. Ver, parar y borrar
```bash
./hack.sh list               # instancias, puertos y estado
./hack.sh status mi-con      # contenedores y URLs de una instancia
./hack.sh logs mi-con        # logs de la instancia (o de cualquier contenedor: ./hack.sh logs consumer)
./hack.sh stop mi-con        # para la instancia (start mi-con para volver a arrancarla)
./hack.sh rm mi-con          # la borra con sus volúmenes y su configuración
```

## Si algo falla
- **"Docker no responde"**: arranca Docker Desktop y espera a que esté en verde.
- **Un servicio no llega a sano**: `./hack.sh logs <contenedor>`. Los `*-setup` son tareas de una sola ejecución: si fallan, su log dice por qué.
- **Error de puerto ocupado en el mini base**: algo de tu equipo usa ya el 1100, 1200, 1300, 1400, 1450, 1500, 6379 o 6380. Ciérralo y repite `./hack.sh base up`.
- **Error al descargar imágenes**: revisa tu conexión y los valores de `versions.env`.
- **Linux: el onboarding no llega a `host.docker.internal`**: el firewall (ufw/firewalld) bloquea el tráfico de Docker hacia el host. Permite la interfaz `docker0`.
- **Datos raros o empezar de cero**: `./hack.sh base reset` para el mini base, o `./hack.sh rm <nombre>` y vuelve a crear la instancia.
