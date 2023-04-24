# Generated by Django 4.1.5 on 2023-03-18 00:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0006_chatroom_is_closed"),
    ]

    operations = [
        migrations.RenameField(
            model_name="chatroom",
            old_name="deleted_at",
            new_name="closed_at",
        ),
        migrations.RemoveField(
            model_name="chatroom",
            name="is_deleted",
        ),
    ]