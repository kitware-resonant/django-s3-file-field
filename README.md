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
Note:
 * edit the `.env` file and remove the whitespaces around the `=` characters
 * Moreover, prepend `export ` to each line, such that it will look like:
 ```bash
 export AWS_REGION=us-east-1
 ```


### Init Django
```sh
pipenv --python=3
cd django
pip install -r requirements.txt
./manage.py migrate
./manage.py createsuperuser
```

### Init Widget Client
```sh
cd django/s3widget/web
npm install
npm run dev
```

### Init Test Vue Client
```sh
cd vue
yarn
```

```sh
cd django
./manager.py runserver
```
--> run at http://localhost:8000 and http://localhost:8000/admin

Example blob forms:
 * http://localhost:8000/blob/
 * http://localhost:8000/blob/new/
 * http://127.0.0.1:8000/admin/joist/blob

```sh
cd vue
yarn serve
```
--> run at http://localhost:8080
