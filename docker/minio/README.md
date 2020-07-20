# girder/minio-nonroot
A MinIO server with an existing non-root user.

## Usage
Run with:
```bash
docker run -p 9000:9000 girder/minio-nonroot
```

Or using Docker Compose:
```yaml
services:
  minio:
    image: girder/minio-nonroot
    ports:
      - 9000:9000
```

The image provides two sets of hardcoded MinIO credentials:
* Root user: `minioRootAccessKey` / `minioRootSecretKey`
* Non-root user: `minioUserAccessKey` / `minioUserSecretKey`
