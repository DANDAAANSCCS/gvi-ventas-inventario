"""Envio de correos via SMTP (Gmail). Fallback a log si SMTP no esta configurado."""
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from config import settings

logger = logging.getLogger(__name__)


def _build_reset_email(to_email: str, reset_url: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "Recupera tu contraseña — GesVentas"
    from_email = settings.smtp_from or settings.smtp_user
    msg["From"] = formataddr((settings.smtp_from_name, from_email))
    msg["To"] = to_email

    # Texto plano para clientes que no soportan HTML.
    msg.set_content(
        "Hola,\n\n"
        "Recibimos una solicitud para restablecer la contraseña de tu cuenta en GesVentas.\n\n"
        f"Abre el siguiente enlace para crear una nueva contraseña (válido por {settings.reset_token_expire_minutes} minutos):\n"
        f"{reset_url}\n\n"
        "Si no solicitaste este cambio puedes ignorar este correo; tu contraseña actual seguirá siendo válida.\n\n"
        "— Equipo GesVentas",
        charset="utf-8",
    )

    html = f"""\
<!doctype html>
<html lang="es">
  <head><meta charset="utf-8"/></head>
  <body style="margin:0;padding:24px;background:#f5f6fa;font-family:Arial,Helvetica,sans-serif;color:#333">
    <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:12px;padding:32px;box-shadow:0 2px 8px rgba(0,0,0,.06)">
      <h1 style="margin:0 0 16px;color:#111;font-size:22px">Recupera tu contraseña</h1>
      <p style="line-height:1.6">Recibimos una solicitud para restablecer la contraseña de tu cuenta en <strong>GesVentas</strong>.</p>
      <p style="line-height:1.6">Haz clic en el botón de abajo para crear una nueva contraseña. El enlace es válido por <strong>{settings.reset_token_expire_minutes} minutos</strong>.</p>
      <p style="text-align:center;margin:28px 0">
        <a href="{reset_url}"
           style="display:inline-block;background:#4f46e5;color:#fff;text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:600">
          Restablecer contraseña
        </a>
      </p>
      <p style="font-size:13px;color:#666;line-height:1.5">
        Si el botón no funciona, copia y pega esta URL en tu navegador:<br/>
        <span style="word-break:break-all;color:#4f46e5">{reset_url}</span>
      </p>
      <hr style="margin:24px 0;border:none;border-top:1px solid #eee"/>
      <p style="font-size:12px;color:#888;line-height:1.5">
        Si no solicitaste este cambio puedes ignorar este correo; tu contraseña actual seguirá siendo válida.
      </p>
    </div>
  </body>
</html>
"""
    msg.add_alternative(html, subtype="html", charset="utf-8")
    return msg


def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """Envia el correo con el enlace de reset. Devuelve True si se envio."""
    if not settings.smtp_enabled:
        # Modo dev: simplemente loggeamos la URL, util para testear sin SMTP real.
        logger.warning("[email_service] SMTP no configurado. Reset URL para %s: %s", to_email, reset_url)
        return False

    try:
        msg = _build_reset_email(to_email, reset_url)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        logger.info("[email_service] Email de reset enviado a %s", to_email)
        return True
    except Exception:
        logger.exception("[email_service] Error enviando email a %s", to_email)
        return False
