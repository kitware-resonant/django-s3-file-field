from django.db import migrations, models

import s3_file_field.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Resource',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('legacy_optional_blob', models.FileField(blank=True, upload_to='')),
                (
                    's3ff_mandatory_blob',
                    s3_file_field.fields.S3FileField(
                        max_length=2000,
                        upload_to=s3_file_field.fields.S3FileField.uuid_prefix_filename,
                    ),
                ),
                (
                    's3ff_optional_blob',
                    s3_file_field.fields.S3FileField(
                        blank=True,
                        max_length=2000,
                        upload_to=s3_file_field.fields.S3FileField.uuid_prefix_filename,
                    ),
                ),
            ],
        ),
    ]
