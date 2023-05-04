from django.db import models

from apps.user.models import User, TimeStampMixin


class Chatroom(TimeStampMixin):
    id = models.BigAutoField(primary_key=True)
    host = models.ForeignKey(User, on_delete=models.CASCADE)
    guest = models.CharField(max_length=20, null=False, blank=False)
    name = models.CharField(max_length=22, null=False, blank=False)
    latest_msg = models.CharField(max_length=2000, null=True)
    latest_msg_at = models.DateTimeField(null=True)
    last_checked_at = models.DateTimeField(null=True)
    is_closed = models.BooleanField(default=False, null=False)
    closed_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "chatroom"

    def __str__(self):
        return f"[{self.id}] {self.host}-{self.guest}"

    def __repr__(self):
        return f"Chatroom({self.id}, {self.host}, {self.guest})"


class ChatMessage(models.Model):
    id = models.BigAutoField(primary_key=True)
    chatroom = models.ForeignKey(Chatroom, on_delete=models.DO_NOTHING)
    message = models.CharField(max_length=2000, null=False)
    is_host = models.BooleanField(null=False, blank=False)
    datetime = models.DateTimeField(null=False)

    class Meta:
        db_table = "chat_message"

    def __str__(self):
        return f"[{self.id}] chatroom: {self.chatroom_id}"

    def __repr__(self):
        return f"ChatMessage({self.id}, {self.chatroom_id})"
