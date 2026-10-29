/**
 * The value which clears an existing file.
 *
 * Otherwise, a value is a pending upload's signed FieldValue (which this can never be mistaken
 * for), or empty, which keeps any existing file. Kept identical in the Django widget.
 */
export const CLEAR_VALUE = 's3ff:clear';

/** The state of the file the element represents, derived from its properties. */
export type FileState =
  /** A pending upload, whose signed FieldValue is submitted; its name may be unknown. */
  | { kind: 'pending'; fieldValue: string; name: string }
  /** The existing file is cleared, by submitting the clear value. */
  | { kind: 'cleared' }
  /** The existing file is kept, by submitting nothing. */
  | { kind: 'kept'; url: string; name: string }
  /** No file, so nothing is submitted. */
  | { kind: 'none' };

export interface FileStateInputs {
  value: string;
  existingUrl: string;
  pendingName: string;
  uploadedFileName: string;
}

/**
 * The final path component of a URL, as the file's name for display.
 *
 * Any query or fragment is dropped, and percent-encoding is decoded.
 */
const QUERY_OR_FRAGMENT = /[?#]/u;
function basename(url: string): string {
  const path = url.split(QUERY_OR_FRAGMENT, 1)[0] ?? '';
  const name = path.split('/').pop() ?? '';
  try {
    return decodeURIComponent(name);
  } catch {
    return name;
  }
}

/**
 * Derive the file state from the element's properties.
 *
 * An existing (already saved) file is known of exactly when its URL is given; it is then kept
 * unless the value says otherwise, and the user can't make it unknown.
 */
export function deriveFileState(inputs: FileStateInputs): FileState {
  if (inputs.value === CLEAR_VALUE) {
    return { kind: 'cleared' };
  }
  if (inputs.value) {
    return {
      kind: 'pending',
      fieldValue: inputs.value,
      // A file uploaded here is named locally; a server-rendered pending value is named by the
      // server, if it could
      name: inputs.uploadedFileName || inputs.pendingName,
    };
  }
  if (inputs.existingUrl) {
    return { kind: 'kept', url: inputs.existingUrl, name: basename(inputs.existingUrl) };
  }
  return { kind: 'none' };
}

/** The form value to submit for a file state: a value, the clear value, or omission. */
export function formValueFor(fileState: FileState): string | null {
  switch (fileState.kind) {
    case 'pending':
      return fileState.fieldValue;
    case 'cleared':
      return CLEAR_VALUE;
    default:
      return null;
  }
}
