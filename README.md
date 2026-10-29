# Nexo · Acortador de enlaces en AWS

Aplicación con HTML, CSS y JavaScript en **S3**, una API **FastAPI en EC2** y persistencia en **DynamoDB**. El backend genera un UUID v4 y devuelve una redirección HTTP 307 al abrir el enlace.

- [Aplicación publicada](http://nexo-acortador-frontendbucket-fg64zfafebef.s3-website-us-east-1.amazonaws.com/)
- [Documentación de la API](http://13.216.86.173:8000/docs)
- Región: `us-east-1`. Stack: `nexo-acortador`.

## Estructura

```text
backend/app/        API, configuración, validación, servicio y acceso a DynamoDB
frontend/           HTML, CSS, JavaScript y dirección de la API
deploy/             Servicio systemd para EC2
infrastructure/     Plantilla CloudFormation de los recursos AWS
scripts/run_local.py  Demo local sin credenciales AWS
tests/              Pruebas de los endpoints y la persistencia
```

## Ejecutar localmente

Requiere Python 3.12 o posterior y Git. Abre una terminal de PowerShell:

```powershell
git clone https://github.com/JosueRBorja/acortador-enlaces-aws.git
cd acortador-enlaces-aws
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts\run_local.py
```

Abre [http://127.0.0.1:5500](http://127.0.0.1:5500). La demo inicia interfaz y API con DynamoDB simulado mediante Moto; no usa AWS. Los datos se borran al detenerla con **Ctrl+C**. Los puertos 5500 y 8000 deben estar libres.

Para ejecutar el backend contra una tabla real, copia `.env.example` a `.env`, configura región, tabla, URL pública y orígenes CORS. Utiliza un perfil AWS autorizado en tu equipo o el rol IAM de EC2; no guardes claves en el código ni en `.env`.

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

`requirements.txt` fija las dependencias de ejecución; `requirements-dev.txt` añade las herramientas de desarrollo.

## API

| Método y ruta | Respuesta |
| --- | --- |
| `POST /shorten` | 201 con `short_code`, `original_url`, `short_url` y `created_at` |
| `GET /{short_code}` | 307 y cabecera `Location` hacia la URL original |
| `GET /urls/{short_code}` | 200 con UUID, URL original y fecha UTC |
| `GET /health` | 200 si el proceso está activo |

Cuerpo de ejemplo para `POST /shorten`:

```json
{"original_url": "https://www.example.com/"}
```

Un UUID inexistente devuelve **404**, una URL inválida **422** y un fallo de almacenamiento **503**. Solo se admiten URLs HTTP/HTTPS sin credenciales embebidas. La tabla utiliza `short_code` como clave de partición String; cada elemento incluye `original_url` y `created_at` en UTC.

## Despliegue en AWS

1. Publica el código en un repositorio público de GitHub o GitLab.
2. En EC2 crea un par de claves y guarda su archivo privado fuera del repositorio.
3. En CloudFormation carga `infrastructure/stack.yaml`. Indica el repositorio HTTPS, rama `main`, nombre del par de claves y tu IPv4 pública seguida de `/32` para SSH.
4. Reconoce la creación del rol IAM y espera `CREATE_COMPLETE`. EC2 instala el backend desde GitHub y configura systemd; esta instalación puede tardar unos minutos adicionales.
5. En las salidas de la pila copia `ApiUrl` a `API_BASE_URL` de `frontend/config.js` para la versión que publicarás.
6. Sube `index.html`, `styles.css`, `app.js` y `config.js` a la raíz del bucket indicado en `BucketName`. Abre `WebsiteUrl`.

El rol de EC2 permite únicamente `dynamodb:GetItem` y `dynamodb:PutItem` sobre su tabla. Boto3 obtiene credenciales temporales del rol. La API permite el origen exacto de S3 mediante CORS. SSH está restringido a `/32`; el puerto 8000 es público. La plantilla publica la interfaz mediante el endpoint web HTTP de S3; usar HTTPS requiere configurarlo también en la API.

En EC2 puedes comprobar y reiniciar el servicio:

```bash
sudo systemctl status nexo --no-pager
sudo journalctl -u nexo -n 30 --no-pager
sudo systemctl restart nexo
```

## Pruebas y entrega

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Las **14 pruebas** verifican creación, UUID únicos, validación, consulta, redirección 307, errores 404, CORS, fallos de almacenamiento y persistencia al recrear la aplicación usando DynamoDB emulado.

El despliegue real fue verificado el **29 de octubre de 2026**: formulario y copiado desde S3, registro consultado en DynamoDB, redirección en el navegador y funcionamiento del mismo enlace después de reiniciar systemd. UUID usado: `5d12b480-cf5c-47c9-bee3-ab1a45f35f63`.

Para la entrega, presenta este repositorio y un video mostrando la arquitectura, el rol IAM, S3, EC2, la tabla y el recorrido completo de un enlace, incluyendo 404, consulta JSON y persistencia tras reiniciar el backend.

Los recursos activos pueden generar cargos. Después de la evaluación puedes eliminar la pila; S3 y DynamoDB se retienen y deben eliminarse manualmente si ya no necesitas sus datos.
