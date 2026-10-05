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
  /** The existing file is kept, by submitting nothing; its URL (and so its name) may be unknown. */
  | { kind: 'kept'; url: string; name: string }
  /** No file, so nothing is submitted. */
  | { kind: 'none' };

export interface FileStateInputs {
  value: string;
  existingFileKnown: boolean;
  existingUrl: string;
  uploadedFileName: string;
}

/**
 * The final path component of a URL or storage key, as the file's name for display.
 *
 * Any query or fragment is dropped, and percent-encoding is decoded.
 */
const QUERY_OR_FRAGMENT = /[?#]/;
function basename(urlOrKey: string): string {
  const path = urlOrKey.split(QUERY_OR_FRAGMENT, 1)[0] ?? '';
  const name = path.split('/').pop() ?? '';
  try {
    return decodeURIComponent(name);
  } catch {
    return name;
  }
}

export function deriveFileState(inputs: FileStateInputs): FileState {
  if (inputs.value === CLEAR_VALUE) {
    return { kind: 'cleared' };
  }
  if (inputs.value) {
    return {
      kind: 'pending',
      fieldValue: inputs.value,
      // A server-rendered pending value is named by its storage key, given as the "URL"
      name: inputs.uploadedFileName || basename(inputs.existingUrl),
    };
  }
  if (inputs.existingFileKnown) {
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

/**
 * Whether the server-rendered properties represent an existing (already saved) file.
 *
 * The server doesn't state this directly, but it follows from how each case is rendered:
 * - a kept existing file has its URL rendered, with no value;
 * - a pending upload has its value rendered, with that upload's own storage key as the "URL" (in
 *   place of any existing file's, which is then unknown);
 * - a clear has the clear value rendered alone, and only an existing file can be cleared.
 */
export function hasExistingFile(inputs: { value: string; existingUrl: string }): boolean {
  if (inputs.value === CLEAR_VALUE) {
    return true;
  }
  if (inputs.value) {
    return false;
  }
  return Boolean(inputs.existingUrl);
}
