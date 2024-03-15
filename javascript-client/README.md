# django-s3-file-field-client
[![npm](https://img.shields.io/npm/v/django-s3-file-field)](https://www.npmjs.com/package/django-s3-file-field)

A Javascript (with TypeScript support) client library for django-s3-file-field.

## Installation
```bash
npm install django-s3-file-field
```

or

```bash
yarn add django-s3-file-field
```

## Usage
```typescript
import axios from 'axios';
import S3FileFieldClient, { S3FileFieldProgress, S3FileFieldProgressState } from 'django-s3-file-field';

function onUploadProgress (progress: S3FileFieldProgress) {
  if (progress.state == S3FileFieldProgressState.Sending) {
    console.log(`Uploading ${progress.uploaded} / ${progress.total}`);
  }
}

const apiClient = axios.create(...); // This can be used to set authentication headers, etc.

const s3ffClient = new S3FileFieldClient({
  baseUrl: process.env.S3FF_BASE_URL, // e.g. 'http://localhost:8000/api/v1/s3-upload/', the path mounted in urlpatterns
  apiConfig: apiClient.defaults, // This argument is optional
});

// This might be run in an event handler
const file = document.getElementById('my-file-input').files[0];

const fieldValue = await s3ffClient.uploadFile(
  file,
  'core.File.blob', // The "<app>.<model>.<field>" to upload to,
  onUploadProgress, // This argument is optional
);

apiClient.post(
  'http://localhost:8000/api/v1/file/', // This is particular to the application
  {
    'blob': fieldValue, // This should match the field uploaded to (e.g. 'core.File.blob')
    ...: ...,  // Other fields for the POST request
  }
);
```
