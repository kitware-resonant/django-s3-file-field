# joist

[![PyPI version shields.io](https://img.shields.io/pypi/v/joist.svg)](https://pypi.python.org/pypi/joist/)

Joist is a Django Widget library for providing a direct S3 bucket upload via the browser instead of going through the server.



## development environment

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
