## Development Environment

### Requirements
 * Python 3.7
 * node
 * AWS CLI (AWS setup)
 * Terraform (AWS setup)
 * docker + docker-compose (MinIO docker setup)


### AWS
#### Init AWS
login to AWS Concole and create an API access key
```sh
aws configure
```

#### Run Terraform
```sh
cd terraform
terraform init
terraform workspace new <NAME>
terraform apply
```

#### Create env File
```sh
cd terraform
terraform output > ../example/.env
```
Note:
 * edit the `.env` file and remove the whitespaces around the `=` characters


### MinIO
#### Create env File

create a `example/.env` file and add these entries:
```
MINIO_STORAGE_MEDIA_BUCKET_NAME=test
MINIO_ACCESS_KEY=rootAccessKey
MINIO_SECRET_KEY=secretWithAtLeast8Characters
MINIO_STORAGE_ACCESS_KEY=actuallAccessKey
MINIO_STORAGE_SECRET_KEY=secretWithAtLeast8Characters
```

#### init MinIO
```sh
docker-compose up -d
```

check logs using `docker-compose logs` it should start up normally and it should have created the user and bucket automatically



### Init Django and Python Repo
```sh
pipenv install --skip-lock
pipenv shell
cd example
./manage.py migrate
./manage.py createsuperuser
```

### Init Repo Pre Commits
```sh
pipenv shell
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
npm install
```


## Run Example Application and Client

### Django
```sh
cd example
./manager.py runserver
```
--> run at http://localhost:8000 and http://localhost:8000/admin

Example blob forms:
 * http://localhost:8000/
 * http://localhost:8000/new/
 * http://127.0.0.1:8000/admin/blobs/blob


### Frontent Vue client
```sh
cd example-client
npm run serve
```
--> run at http://localhost:8080


### Release

```sh
pipenv shell
bumpversion minor
```

TODO: npm release
