# Generated by Django 2.2.7 on 2019-11-18 22:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blobs', '0001_add_blob_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='blob',
            name='r2',
            field=models.FileField(null=True, upload_to=''),
        ),
    ]
