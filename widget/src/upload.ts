import S3FileFieldClient, { type S3FileFieldProgressCallback } from 'django-s3-file-field';

/**
 * Find the CSRF token, which Django's protection requires to be sent back with a session.
 *
 * A Django-rendered form carries the token as a hidden input, which works in any context, with
 * an HttpOnly cookie, and with a renamed cookie. Without such a form (as when the element is
 * driven by a frontend framework), the CSRF cookie is read instead, which the Cookie Store API
 * allows only in a secure context; elsewhere the upload fails with an error naming the cause.
 */
async function getCsrfToken(form: HTMLFormElement | null): Promise<string | undefined> {
  const input = form?.elements.namedItem('csrfmiddlewaretoken');
  if (input instanceof HTMLInputElement) {
    return input.value;
  }
  // The Cookie Store API is not exposed at all in an insecure context. A deployment there is a
  // misconfiguration, so fail with the fix rather than with the server's less specific CSRF error
  // (or, for an anonymous upload, with no token).
  if (typeof cookieStore === 'undefined') {
    throw new Error(
      'The CSRF cookie cannot be read in an insecure context. ' +
        'Serve the page over HTTPS or from localhost, or render the element within a Django form.',
    );
  }
  const cookie = await cookieStore.get('csrftoken');
  return cookie?.value;
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
  crossOriginCookies: boolean,
  authorization: string | undefined,
  onProgress: S3FileFieldProgressCallback,
  signal: AbortSignal,
): Promise<string> {
  const headers: Record<string, string> = {};
  if (authorization === undefined) {
    // Django REST framework enforces CSRF only for session authentication, so the token is
    // needed only without an Authorization header
    const csrfToken = await getCsrfToken(form);
    if (csrfToken !== undefined) {
      headers['X-CSRFToken'] = csrfToken;
    }
  } else {
    headers.Authorization = authorization;
  }
  const client = new S3FileFieldClient({
    baseUrl,
    apiConfig: {
      // Cookies are sent with same-origin requests either way; "include" also sends them
      // cross-origin, where the response must then allow credentials from this origin.
      // If the server does not enable SessionAuthentication, requests will be unauthenticated,
      // but still allowed.
      credentials: crossOriginCookies ? 'include' : 'same-origin',
      headers,
    },
  });
  return client.uploadFile(file, fieldId, onProgress, signal);
}
