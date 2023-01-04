# Generated by Django 4.1.5 on 2023-01-04 09:02

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatroom",
            name="host",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="chatroom",
            name="latest_msg",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="latest_msg",
                to="chat.chatmessage",
            ),
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="chatroom",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="chat.chatroom"
            ),
        ),
    ]
