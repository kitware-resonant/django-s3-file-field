import Cookies from "js-cookie";

/**
 * @internal
 */
export const DEFAULT_BASE_URL = "/api/joist";


export const EVENT_UPLOAD_STARTED = 's3UploadStarted';
export const EVENT_UPLOAD_COMPLETE = 's3UploadComplete';

/**
 * @internal
 */
export function fetchOptions(): RequestInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json"
  };
  // for django
  const csrftoken = Cookies.get("csrftoken");
  if (csrftoken) {
    headers["X-CSRFToken"] = csrftoken;
  }
  return {
    credentials: "same-origin",
    headers
  };
}
