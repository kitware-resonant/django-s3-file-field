# S3 File Field example

This provides an example Django project, `s3ff_example`,
for use in local development and debugging.

Some settings used here are not appropriate for production use.

# Setup
* In a separate terminal:
  ```bash
  docker-compose up
  ```

* In the main terminal:
  ```bash
  pip install -e ..[dev]
  ./manage.py migrate
  ```

* To allow usage of the admin page:
  ```bash
  ./manage.py createsuperuser
  ```

# Run
* Ensure `docker-compose up` is still running

* In the main terminal:
  ```bash
  ./manage.py runserver
  ```

* Load http://localhost:8000/ in a web browser
