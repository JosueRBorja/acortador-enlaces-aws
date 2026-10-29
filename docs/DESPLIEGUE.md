# Despliegue en AWS paso a paso

Usa tu cuenta de práctica y una región única, por ejemplo **us-east-1**. EC2, IPv4 pública, EBS, DynamoDB, sus respaldos y S3 pueden generar cargos; revisa el presupuesto y las condiciones de tu cuenta. La plantilla retiene S3 y DynamoDB al borrar el stack para proteger los enlaces.

## 1. Repositorio y entorno

El repositorio destinado a esta práctica es `https://github.com/JosueRBorja/acortador-enlaces-aws`. Publica estos archivos en la rama `main`. No subas `.venv`, `.env`, archivos PEM ni credenciales.

La instalación automática de EC2 clona un repositorio **público** por HTTPS. Si es privado, necesitarás un mecanismo de entrega autenticado diferente; no incluyas tokens en el parámetro RepositoryUrl ni en UserData. Comprueba antes que los archivos estén disponibles en `main`, especialmente `requirements.lock.txt`.

Para publicar desde una copia local ya vinculada al repositorio:

```powershell
git add .
git commit -m "Implementar acortador con FastAPI, S3, EC2 y DynamoDB"
git push -u origin main
```

## 2. Par de claves y dirección SSH

1. En AWS Console selecciona la región elegida.
2. Ve a **EC2 → Key pairs → Create key pair**. Usa RSA y `.pem`, y guarda la clave en un lugar privado fuera del repositorio.
3. Obtén tu dirección IPv4 pública desde la información de tu conexión o un servicio de consulta de IP. El parámetro SSH será `TU_IP/32`. Si cambia tu IP, actualiza el stack. No uses `0.0.0.0/0` para SSH.

## 3. Crear la infraestructura

1. Abre **CloudFormation → Create stack → With new resources**.
2. Elige cargar un archivo y selecciona `infrastructure/stack.yaml` de este proyecto.
3. Nombre del stack: `nexo-acortador`.
4. Completa:
   - `RepositoryUrl`: `https://github.com/JosueRBorja/acortador-enlaces-aws.git`.
   - `RepositoryRef`: `main` (o una etiqueta de versión existente).
   - `KeyName`: nombre del par de claves recién creado.
   - `SshCidr`: tu IPv4 seguida de `/32`.
   - `UbuntuAmi`: conserva el parámetro SSM de Ubuntu 24.04.
5. Revisa los recursos y reconoce la creación de recursos IAM. Crea el stack.
6. Espera `CREATE_COMPLETE`. Guarda sus **Outputs**: `WebsiteUrl`, `BucketName`, `ApiUrl`, `ApiDocs`, `TableName`, `InstanceId` y `PublicIp`.

La plantilla crea una VPC con acceso a Internet, una EC2 Ubuntu `t3.micro`, un volumen cifrado, una IP elástica estable, un bucket web, una tabla DynamoDB bajo demanda y el rol IAM. Solo permite SSH desde tu IP; la API 8000 es pública porque los navegadores de los visitantes la consumen directamente.

El rol de EC2 contiene únicamente `dynamodb:GetItem` y `dynamodb:PutItem` en el ARN de la tabla. No permite Scan, DeleteItem ni acceso a otras tablas. No incluye acceso de escritura a S3: los archivos de interfaz se suben desde tu sesión de despliegue.

**Importante:** `CREATE_COMPLETE` confirma la infraestructura, pero no espera a que termine el script de instalación de EC2. Abre `ApiUrl/health` y luego `ApiDocs`; si no responden tras varios minutos, revisa el paso siguiente.

## 4. Verificar EC2 y systemd

Conéctate desde una terminal usando la clave y `PublicIp`:

```bash
ssh -i /ruta/privada/nexo.pem ubuntu@IP_PUBLICA
sudo cloud-init status --wait
sudo systemctl status nexo --no-pager
sudo journalctl -u nexo -n 50 --no-pager
```

La instalación usa `/opt/nexo`, crea su entorno virtual, instala las versiones fijadas y guarda la configuración en `/etc/nexo.env`, legible solo por root y el grupo del servicio. El código permanece propiedad de root. El servicio utiliza el usuario `nexo` y escucha en `0.0.0.0:8000`.

Comprueba `/etc/nexo.env` mediante `sudo cat /etc/nexo.env`: debe contener región, tabla, `PUBLIC_BASE_URL` con la IP elástica, y `CORS_ORIGINS` con el valor exacto de `WebsiteUrl`. No hay claves AWS en ese archivo. Boto3 obtiene credenciales temporales del rol adjunto a EC2.

Si falló la instalación, consulta `sudo tail -n 100 /var/log/cloud-init-output.log`. Revisa primero que el repositorio sea público y que `main` contenga el proyecto. Para completar una instalación después de corregir archivos, ejecuta los pasos faltantes del bloque UserData de la plantilla; no vuelvas a crear usuarios existentes sin comprobarlo. La actualización del código requiere un `git pull`, reinstalar dependencias si cambiaron y reiniciar el servicio; modificar `RepositoryRef` en CloudFormation no garantiza que UserData se vuelva a ejecutar.

## 5. Publicar los archivos del frontend en S3

1. En tu copia local edita `frontend/config.js`: cambia `API_BASE_URL` por **ApiUrl** del stack, sin barra final.
2. Ve a **S3 → bucket indicado en BucketName → Upload**.
3. Sube los cuatro archivos **en la raíz**: `index.html`, `styles.css`, `app.js` y `config.js`. No subas la carpeta `frontend` como un nivel adicional.
4. Comprueba tipos MIME: `text/html`, `text/css` y `application/javascript` para los JS. La consola suele inferirlos por extensión.
5. Abre exactamente **WebsiteUrl**, que comienza con `http://`. No uses el endpoint REST del bucket ni fuerces `https://`.

La plantilla habilita publicación web y una política de lectura pública solo de objetos. Conserva bloqueo de ACL públicas y propiedad del bucket. Si el stack falla por bloqueo de políticas públicas a nivel de cuenta o una política de tu institución, no desactives protecciones globales indiscriminadamente: utiliza un bucket privado detrás de CloudFront con OAC y configura también HTTPS en la API. Esa alternativa requiere adaptar esta plantilla y un dominio/certificado para el backend.

Si tienes AWS CLI autenticada en una sesión de administración, puedes subir los archivos con:

```bash
aws s3 sync frontend/ s3://NOMBRE_BUCKET/ --exclude "config.local.js"
```

## 6. Probar la integración

Sigue todas las pruebas de `docs/ENTREGA.md`. Puedes automatizar las comprobaciones HTTP desde el entorno virtual:

```powershell
.\.venv\Scripts\python.exe scripts\verify_deployment.py --api-url http://IP_PUBLICA:8000 --origin http://BUCKET.s3-website-REGION.amazonaws.com
```

Usa el origen real de **WebsiteUrl**, cuyo formato varía según región. La prueba crea un registro real en DynamoDB. También debes demostrar el formulario en el navegador, el elemento en la consola de DynamoDB y la persistencia después del reinicio real de systemd.

## Diagnóstico

| Síntoma | Comprobación |
| --- | --- |
| API no responde | Estado systemd, cloud-init, entrada TCP 8000, IP elástica y ruta a Internet |
| POST devuelve 503 | Rol adjunto a EC2, GetItem/PutItem, región y nombre exacto de la tabla |
| Error CORS | Comparar origen completo (protocolo, dominio, puerto) con `/etc/nexo.env`; reiniciar systemd |
| S3 devuelve 403 | Objetos en raíz, política de bucket, bloqueo público de cuenta y URL de sitio web |
| Página HTTPS no llama API HTTP | Usar los endpoints HTTP académicos o configurar HTTPS en ambos extremos |
| Enlace apunta a localhost | Corregir PUBLIC_BASE_URL y reiniciar el backend; crear otro enlace |
| Copiar no funciona en HTTP | El navegador puede bloquear execCommand; seleccionar el enlace y copiar manualmente |

## Limpieza al finalizar

Después de la evaluación, elimina el stack desde CloudFormation si ya no necesitas el servicio: se terminan EC2, su volumen y la IP elástica. **El bucket y la tabla se retienen**. Si decides eliminar también esos datos, vacía y elimina el bucket y elimina la tabla manualmente desde sus consolas; revisa respaldos y recursos retenidos. Esto borra los enlaces guardados. No borres recursos antes de grabar y verificar la entrega.
