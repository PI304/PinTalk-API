from .base import *

# DEBUG = False
ALLOWED_HOSTS = [
    "13.124.31.67",
    "localhost",
    "127.0.0.1",
]  # 인스턴스 IPv4 기반 퍼블릭 DNS 주소 or 퍼블릭 IP
WSGI_APPLICATION = "config.wsgi.application.deploy"
ASGI_APPLICATION = "config.asgi.application.deploy"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("0.0.0.0", 6379)],
        },
    },
}
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "PORT": 3306,
        "NAME": "pintalk",
        "USER": "root",
        "HOST": "pintalk-db",
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "CONN_MAX_AGE": 60 * 10,  # 10 minutes
        "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
    },
}
