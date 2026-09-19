import S3FileFieldClient from 'django-s3-file-field';

/**
 * Upload a file for an S3FileField, returning its signed FieldValue.
 *
 * This wraps the JavaScript client, configuring it for a browser session with the Django server.
 */
export async function uploadFile(baseUrl: string, fieldId: string, file: File): Promise<string> {
  const client = new S3FileFieldClient({
    baseUrl,
    apiConfig: {
      // This will cause session and CSRF cookies to be sent for same-site requests.
      // Cross-site requests with the server-rendered widget are not supported.
      // If the server does not enable SessionAuthentication, requests will be unauthenticated,
      // but still allowed.
      xsrfCookieName: 'csrftoken',
      xsrfHeaderName: 'X-CSRFToken',
      // Explicitly disable this, to ensure that cross-site requests fail cleanly.
      withCredentials: false,
    },
  });
  return client.uploadFile(file, fieldId);
}
