# Despliegue y configuración SMTP

Pasos mínimos para configurar envío SMTP en producción:

1. Variables de entorno (recomendado) o archivo `.env` en `App/config/.env`:
   - `SMTP_SERVER` — servidor SMTP (ej. smtp.gmail.com)
   - `SMTP_PORT` — puerto (ej. 587)
   - `SMTP_USERNAME` — usuario para autenticación (opcional)
   - `SMTP_PASSWORD` — contraseña para autenticación (opcional)
   - `SMTP_USE_TLS` — `true` o `false`
   - `SMTP_FROM` — dirección `From` por defecto

2. Ejemplo `.env`:

```
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=usuario
SMTP_PASSWORD=secreto
SMTP_USE_TLS=true
SMTP_FROM=noreply@example.com
```

3. Cómo pasar la configuración a `procesar_envio`:

```
smtp_config = {
    'server': os.environ.get('SMTP_SERVER'),
    'port': int(os.environ.get('SMTP_PORT', 587)),
    'username': os.environ.get('SMTP_USERNAME'),
    'password': os.environ.get('SMTP_PASSWORD'),
    'use_tls': os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true',
    'from_addr': os.environ.get('SMTP_FROM'),
}

procesar_envio(..., dry_run=False, smtp_config=smtp_config)
```

4. Seguridad:
   - No guardar credenciales en el repositorio.
   - Usar secretos del CI/CD o un vault para producción.

5. Pruebas:
   - Ejecutar `App/run_dry_run_envio.py` con `dry_run=True` antes de habilitar `dry_run=False`.
