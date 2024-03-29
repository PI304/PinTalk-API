# Generated by Django 4.1.5 on 2023-01-04 09:02

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("message", models.CharField(max_length=2000)),
                ("is_host", models.BooleanField()),
            ],
            options={
                "db_table": "chat_message",
            },
        ),
        migrations.CreateModel(
            name="Chatroom",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "visitor",
                    models.CharField(blank=True, default="Guest", max_length=20),
                ),
            ],
            options={
                "db_table": "chatroom",
            },
        ),
    ]
