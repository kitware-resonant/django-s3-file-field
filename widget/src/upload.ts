import S3FileFieldClient, { type S3FileFieldProgressCallback } from 'django-s3-file-field';

/**
 * Find the CSRF token, which Django's protection requires to be sent back with a session.
 *
 * A Django-rendered form carries the token as a hidden input, which works in any context, with
 * an HttpOnly cookie, and with a renamed cookie. Without such a form (as when the element is
 * driven by a frontend framework), the CSRF cookie is read instead, which the Cookie Store API
 * allows only in a secure context.
 */
async function getCsrfToken(form: HTMLFormElement | null): Promise<string | undefined> {
  const input = form?.elements.namedItem('csrfmiddlewaretoken');
  if (input instanceof HTMLInputElement) {
    return input.value;
  }
  return 'cookieStore' in globalThis ? (await cookieStore.get('csrftoken'))?.value : undefined;
}

/**
 * Upload a file for an S3FileField, returning its signed FieldValue.
 *
 * This wraps the JavaScript client, configuring it for a browser session with the Django server.
 */
// biome-ignore lint/complexity/useMaxParams: positional arguments read fine at the one call site
export async function uploadFile(
  baseUrl: string,
  fieldId: string,
  file: File,
  form: HTMLFormElement | null,
  onProgress: S3FileFieldProgressCallback,
): Promise<string> {
  const csrfToken = await getCsrfToken(form);
  const client = new S3FileFieldClient({
    baseUrl,
    apiConfig: {
      // Session and CSRF cookies are sent with same-origin requests only.
      // Cross-origin requests with the server-rendered widget are not supported, and this
      // ensures that they fail cleanly.
      // If the server does not enable SessionAuthentication, requests will be unauthenticated,
      // but still allowed.
      credentials: 'same-origin',
      headers: csrfToken === undefined ? {} : { 'X-CSRFToken': csrfToken },
    },
  });
  return client.uploadFile(file, fieldId, onProgress);
}
