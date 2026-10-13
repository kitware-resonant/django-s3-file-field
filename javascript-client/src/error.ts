import { isHTTPError, isNetworkError, isTimeoutError, type KyError } from 'ky';

import type { S3FileFieldProgressState } from './client.js';
import type { ErrorResponse } from './types.js';

/**
 * The explanation in the API's JSON error body, when it gives one.
 *
 * The API describes an error in JSON, like:
 *   {"detail": "Upload size is too large."}
 * or, for invalid input, with a list of validation errors, the first of which explains it:
 *   {"detail": [{"type": "missing", "loc": ["file_name"], "msg": "Field required"}]}
 */
function apiErrorDetail(data: object): string | undefined {
  if ('detail' in data) {
    // Is an API error
    const { detail } = data as ErrorResponse;
    return typeof detail === 'string' ? detail : detail.at(0)?.msg;
  }
  return undefined;
}

// S3 describes an error in XML, like:
//   <Error>
//     <Code>InvalidPart</Code>
//     <Message>One or more of the specified parts could not be found.</Message>
//     <RequestId>4442587FB7D0A2F9</RequestId>
//   </Error>
// Anchor the patterns at the start, to avoid possible quadratic backtracking on
// technically-untrusted input.
const s3ErrorCodePattern = /^\s*(?:<\?xml[^>]*>\s*)?<Error>.*?<Code>([^<]*)<\/Code>/s;
const s3ErrorMessagePattern = /^\s*(?:<\?xml[^>]*>\s*)?<Error>.*?<Message>([^<]*)<\/Message>/s;

/** The code of an S3 error, if the body of a response describes one. */
export function s3ErrorCode(body: string): string | undefined {
  return s3ErrorCodePattern.exec(body)?.[1];
}

/** The message of an S3 error, if the body of a response describes one. */
export function s3ErrorMessage(body: string): string | undefined {
  return s3ErrorMessagePattern.exec(body)?.[1];
}

/**
 * The failure of an upload.
 *
 * The message is suitable for display: the server's explanation, when it gave one, or else a
 * description of the failure. The cause is the underlying error (as ky's `HTTPError`) or the
 * response's body, for diagnosis.
 */
export class S3FileFieldError extends Error {
  override readonly name = 'S3FileFieldError';

  /** The stage of the upload which failed. */
  readonly stage: S3FileFieldProgressState;

  /** The HTTP status of the response, if one was received. */
  readonly status: number | undefined;

  /** The server's explanation of the failure, if it gave one. */
  readonly detail: string | undefined;

  constructor(
    stage: S3FileFieldProgressState,
    message: string,
    { status, detail, cause }: { status?: number; detail?: string; cause?: unknown } = {},
  ) {
    super(message, { cause });
    this.stage = stage;
    this.status = status;
    this.detail = detail;
  }

  /** Describe the failure of a request made by ky. */
  static fromKyError(error: KyError, stage: S3FileFieldProgressState): S3FileFieldError {
    if (isHTTPError(error)) {
      const { status } = error.response;
      const { data } = error;
      // ky parses a JSON body (as the API's) and leaves any other (as S3's XML) as text
      let detail: string | undefined;
      if (typeof data === 'string') {
        detail = s3ErrorMessage(data);
      } else if (typeof data === 'object' && data !== null) {
        detail = apiErrorDetail(data);
      }
      return new S3FileFieldError(stage, detail ?? `Upload failed with HTTP ${status}.`, {
        status,
        detail,
        cause: error,
      });
    }
    if (isTimeoutError(error)) {
      return new S3FileFieldError(stage, 'Upload timed out.', { cause: error });
    }
    if (isNetworkError(error)) {
      return new S3FileFieldError(stage, 'Upload failed with a network error.', { cause: error });
    }
    return new S3FileFieldError(stage, 'Upload failed.', { cause: error });
  }
}
