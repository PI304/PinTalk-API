import uuid
import base64
import secrets


def uuid_to_b64uuid():
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode("utf8").rstrip("=\n")


def generate_secret_key():
    return (
        base64.urlsafe_b64encode(
            uuid.uuid5(uuid.NAMESPACE_DNS, uuid_to_b64uuid()).bytes
        )
        .decode("utf8")
        .rstrip("=\n")
    )


def generate_secret():
    return secrets.token_hex(32)


n = generate_secret()

print(n, len(n))
