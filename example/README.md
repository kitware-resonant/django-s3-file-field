# example

`example` is a simple use case for `django-s3-file-field`.

# Setup

## Minio

A Minio instance needs to be running. There is a docker container which makes this easy:

```
docker pull girder/minio-nonroot:latest
docker run --name example-minio girder/minio-nonroot:latest
# Ctrl+C will stop the container, but save the data stored in it
# To restart:
docker start -a example-minio
```

## Dependency Installation

From the parent directory, use `pipenv` to set up a virtual environment and install all required dependencies:

```
pipenv install
pipenv shell
```

## Configuration

The following environment variables need to be set when Django starts.
You can adjust them as necessary for your Minio deployment.

```
export MINIO_ACCESS_KEY=yes
export MINIO_STORAGE_ENDPOINT=localhost:9000
export MINIO_STORAGE_ACCESS_KEY=minioUserAccessKey
export MINIO_STORAGE_SECRET_KEY=minioUserSecretKey
export MINIO_STORAGE_MEDIA_BUCKET_NAME=s3-file-field-example
```

## Start Django

From the `example` directory, run these django commands to initialize the SQLite DB and start the server:

```
python manage.py migrate
python manage.py createsuperuser # create the admin user for this Django instance
python manage.py runserver
```

You should now be able to visit http://localhost:8000/ in your browser and see the app running.
Any files uploaded in the `Add Blob` page will be uploaded to the Minio instance.