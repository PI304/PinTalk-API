# Generated by Django 4.1.5 on 2023-03-18 01:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0007_rename_deleted_at_chatroom_closed_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatroom",
            name="fixed_at",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="chatroom",
            name="is_fixed",
            field=models.BooleanField(default=False, null=True),
        ),
    ]