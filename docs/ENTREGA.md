# Evidencias y video de entrega

Repositorio: https://github.com/JosueRBorja/acortador-enlaces-aws

Completar después de desplegar:

| Evidencia | Valor real |
| --- | --- |
| URL del sitio S3 | Pendiente |
| URL de API EC2 | Pendiente |
| Región AWS | Pendiente |
| Nombre de tabla | Pendiente |
| UUID usado en las pruebas | Pendiente |
| Enlace al video | Pendiente |

## Pruebas obligatorias

- [ ] Abrir WebsiteUrl de S3 y mostrar la interfaz cargada.
- [ ] Ingresar `https://www.example.com/articulos/arquitectura-cloud` o una página real que puedas abrir.
- [ ] Mostrar en las herramientas de red del navegador que se envía POST `/shorten` a EC2 y responde 201 con un UUID v4 generado por el backend.
- [ ] En DynamoDB → tabla → Explore table items, ubicar ese UUID y mostrar `short_code`, `original_url` y `created_at` como un elemento independiente.
- [ ] Copiar y abrir el enlace en otra pestaña; verificar que el navegador navega al destino.
- [ ] Mostrar la respuesta HTTP 307 y la cabecera Location, con herramientas de red conservando el registro o con `curl -i` sin `-L`.
- [ ] Abrir `/550e8400-e29b-41d4-a716-446655440000` (confirmar que ese UUID no fue creado) y mostrar 404.
- [ ] Consultar `/urls/UUID_CREADO` y mostrar su JSON con fecha de creación.
- [ ] Guardar el UUID antes del reinicio; ejecutar `sudo systemctl restart nexo` en EC2 y abrir **el mismo enlace**. Comprobar de nuevo 307 hacia el mismo destino.
- [ ] Opcionalmente reiniciar la instancia y comprobar systemd y el enlace usando su IP elástica estable.
- [ ] Ingresar una URL inválida y comprobar el mensaje. Para probar indisponibilidad, detener temporalmente el servicio, enviar desde el formulario y volver a iniciarlo.

Comandos desde EC2 o una terminal con curl:

```bash
curl -i -X POST http://IP_PUBLICA:8000/shorten -H 'Content-Type: application/json' --data '{"original_url":"https://www.example.com/"}'
curl -i http://IP_PUBLICA:8000/UUID_CREADO
curl -i http://IP_PUBLICA:8000/urls/UUID_CREADO
curl -i http://IP_PUBLICA:8000/550e8400-e29b-41d4-a716-446655440000
```

En Windows usa `curl.exe` para evitar el alias de Windows PowerShell; para crear registros también puedes usar `/docs` y su botón Try it out.

## Guion sugerido del video (7–10 minutos)

1. **Objetivo y arquitectura (1 min).** Presentar las tres piezas: interfaz S3, backend EC2 y persistencia DynamoDB. Explicar el recorrido POST → UUID → PutItem → respuesta y GET → GetItem → redirección.
2. **Repositorio y buenas prácticas (1 min).** Mostrar módulos, separación frontend/backend, entorno virtual, dependencias, `.env.example`, `.gitignore` y pruebas. Mostrar `uuid4()` en `backend/app/service.py` y `RedirectResponse(..., status_code=307)` en `main.py`.
3. **DynamoDB (1 min).** Mostrar clave de partición `short_code` de tipo String, capacidad bajo demanda y registro con URL y fecha UTC. Aclarar que no se usa una base de datos en memoria.
4. **EC2 e IAM (1–2 min).** Mostrar instancia Linux, Security Group con SSH restringido a `/32`, puerto 8000, rol adjunto con únicamente PutItem/GetItem sobre la tabla, variables sin claves estáticas y estado `active` de systemd.
5. **S3 y CORS (1 min).** Mostrar los cuatro archivos publicados, alojamiento web, origen exacto configurado y API_BASE_URL apuntando a EC2. Explicar que el endpoint web de S3 utiliza HTTP; HTTPS requiere otra configuración.
6. **Demostración integral (2 min).** Crear desde S3, comprobar el registro, copiar el enlace, observar 307, consultar JSON y demostrar 404. Mostrar también el manejo de errores.
7. **Persistencia (1 min).** Reiniciar systemd y abrir el UUID creado antes. Cerrar mostrando el repositorio y el sitio accesible.

No mostrar claves PEM, contraseñas ni credenciales durante la grabación. El video debe enseñar recursos y resultados reales de tu cuenta, además del código.
