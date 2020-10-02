## Development Environment

### Requirements
 * Python 3.7
 * node
 * AWS CLI (AWS setup)
 * docker + docker-compose (MinIO docker setup)

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
