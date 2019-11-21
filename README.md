# joist

[![PyPI version shields.io](https://img.shields.io/pypi/v/joist.svg)](https://pypi.python.org/pypi/joist/)

Joist is a Django Widget library for providing a direct S3 bucket upload via the browser instead of going through the server. It extends the [django-storages](https://github.com/jschneier/django-storages) library for the S3 file storage

## Installation

```sh
pip install django-storages joist
```

by source:

```sh
pip install -e 'git+https://github.com/danlamanna/joist.git#egg=joist'
```

## Configuration

Joist depends on the django-storages S3 config (see https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html), following settings are used

| Key                     | Description  |
| ----------------------- | ------------- |
| AWS_ACCESS_KEY_ID       | Your Amazon Web Services access key, as a string. |
| AWS_SECRET_ACCESS_KEY   | Your Amazon Web Services secret access key, as a string. |
| AWS_S3_REGION_NAME      | Name of the AWS S3 region to use (eg. eu-west-1) |
| AWS_STORAGE_BUCKET_NAME | Your Amazon Web Services storage bucket name, as a string.
 |

Additional settings

| Key                     | Description  |
| ----------------------- | ------------- |
| JOIST_UPLOAD_STS_ARN    | The STS Arn Role to use (required) |
| JOIST_UPLOAD_DURATION   | The duration the upload token should be valid in seconds (default: `60*60*12 = 12h`) |
| JOIST_UPLOAD_PREFIX      | Prefix where files should be stored (default: '') |
| JOIST_API_BASE_URL | API prefix where the server urls are hosted (default: 'api/joist')
|


## Usage

### Setup

Add `joist` to the list of installed apps:

`settings.py`:
```python
INSTALLED_APPS = [
    ...
    'rest_framework',
    'rest_framework.authtoken',
    'joist',
]
```

Moreover, since the field requires additional REST endpoints one has to use add them to the `urlpatterns`:

`urls.py`
```python
urlpatterns = [
    ...
    path('api/joist/', include('joist.urls')),
]
```

### Model Definition:

instead of

```python
photo = models.FileField()
```

```python
from joist.models import S3FileField

photo = S3FileField()
```

The result is that once the user select a file in the file chooser, it will be automatically uploaded to S3 on the client side.

## Development Environment

### Requirements
 * Terraform
 * AWS CLI
 * Python 3.7
 * node

## Init AWS
login to AWS Concole and create an API access key
```sh
aws configure
```

### Run Terraform
```sh
cd terraform
terraform init
terraform workspace new <NAME>
terraform apply
```

### Create env File
```sh
cd terraform
terraform output > ../example/.env
```
Note:
 * edit the `.env` file and remove the whitespaces around the `=` characters


### Init Django and Python Repo
```sh
pipenv --python=3
pipenv install -r requirements.txt example/requirements.txt
pip install -e .

cd example
./manage.py migrate
./manage.py createsuperuser
```

### Init Repo Pre Commits
```sh
pipenv shell
pip install pre-commit
pre-commit install
```

### Init Widget Client
```sh
cd client
npm install
npm run dev
```

### Init Test Vue Client
```sh
cd example-client
yarn
```

TODO


```sh
cd example
./manager.py runserver
```
--> run at http://localhost:8000 and http://localhost:8000/admin

Example blob forms:
 * http://localhost:8000/
 * http://localhost:8000/new/
 * http://127.0.0.1:8000/admin/blobs/blob


```sh
cd example-client
yarn serve
```
--> run at http://localhost:8080
