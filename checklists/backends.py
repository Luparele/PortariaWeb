from django.core.mail.backends.smtp import EmailBackend
from .models import EmailConfig

class DynamicEmailBackend(EmailBackend):
    def __init__(self, *args, **kwargs):
        # Try to load config from database
        try:
            config = EmailConfig.objects.first()
            if config:
                kwargs.setdefault('host', config.host)
                kwargs.setdefault('port', config.port)
                kwargs.setdefault('username', config.user)
                kwargs.setdefault('password', config.get_decrypted_password())
                kwargs.setdefault('use_tls', config.use_tls)
                kwargs.setdefault('use_ssl', config.use_ssl)
        except Exception:
            # Fallback to defaults or settings if DB not ready
            pass
            
        super().__init__(*args, **kwargs)
