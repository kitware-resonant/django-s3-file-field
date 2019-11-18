# joist


## development environment

### Requirements
 * Terraform
 * AWS CLI
 * Python 3.7
 * node
 * yarn

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
terraform output > ../django/.env
```
Note: edit the `.env` file and remove the whitespaces around the `=` characters

### Init Django and Python Repo
```sh
pipenv --python=3
cd django
pip install -r requirements.txt
./manage.py migrate
./manage.py createsuperuser
```

### Init Repo Pre Commits
```sh
pipenv shell
pip install pre-commit
pre-commit install
```

### Init Client
```sh
cd vue
yarn
```

### Run
```sh
docker-compose up -d
```

```sh
cd django
./manager.py runserver
```
--> run at http://localhost:8000 and http://localhost:8000/admin

```sh
cd vue
yarn serve
```
--> run at http://localhost:8080
