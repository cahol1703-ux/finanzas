# Changelog

## 2026-06-09 — feature/mime-smtp-attachments
- Implementar envío SMTP con adjuntos usando `EmailMessage` (MIME).
- Añadir fallback Outlook/SMTP y parámetro `dry_run` para pruebas.
- Mejorar `analizar_excel` para detectar reglas con/sin encabezado.
- Exponer `logger` por defecto en `App/Functions/logs_config.py`.
- Añadir `App/run_dry_run_envio.py` para pruebas locales (dry-run).
