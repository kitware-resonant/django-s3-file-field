FROM minio/minio:latest AS builder
# Install MinIO Client (mc)
RUN \
  wget https://dl.min.io/client/mc/release/linux-amd64/mc && \
  chmod +x mc
# The config is encryped with the root credentials MINIO_ACCESS_KEY / MINIO_SECRET_KEY, so
# these must be the same as at runtime.
ENV MINIO_ACCESS_KEY minioRootAccessKey
ENV MINIO_SECRET_KEY minioRootSecretKey
# The MINIO_USER_* variables are not known by MinIO, but are set here for convenient reuse.
ENV MINIO_USER_ACCESS_KEY minioUserAccessKey
ENV MINIO_USER_SECRET_KEY minioUserSecretKey
# * Start the MinIO server in the background
# * Wait for it bo be ready
# * Connect MinIO Client to the running MinIO server
# * Use MinIO Client to add an ordinary user
# * Use MinIO Client to grant the user read-write access to resources on the server
# Set the backend directory to a location other than "/data"! This path is defined as a VOLUME by
# the base image, which breaks the ability to write additional data to it during RUN commands
# within a build. See: https://stackoverflow.com/a/55516433
RUN \
  sh -c "/usr/bin/docker-entrypoint.sh minio server /var/lib/minio &" && \
  until nc -z localhost 9000; do sleep 1; done && \
  ./mc config host add minio http://localhost:9000 ${MINIO_ACCESS_KEY} ${MINIO_SECRET_KEY} && \
  ./mc admin user add minio ${MINIO_USER_ACCESS_KEY} ${MINIO_USER_SECRET_KEY} && \
  ./mc admin policy set minio readwrite user=${MINIO_USER_ACCESS_KEY}

FROM minio/minio:latest
# The config is encryped with the root credentials MINIO_ACCESS_KEY / MINIO_SECRET_KEY, so
# these must be persisted for runtime.
ENV MINIO_ACCESS_KEY minioRootAccessKey
ENV MINIO_SECRET_KEY minioRootSecretKey
COPY --from=builder /var/lib/minio /var/lib/minio
VOLUME /var/lib/minio
CMD ["server", "/var/lib/minio"]
EXPOSE 9000
