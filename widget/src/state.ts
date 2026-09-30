/**
 * The value which clears an existing file.
 *
 * Otherwise, a value is a pending upload's signed FieldValue (which this can never be mistaken
 * for), or empty, which keeps any existing file. Kept identical in the Django widget.
 */
export const CLEAR_VALUE = 's3ff:clear';

/** The state of the file the element represents, derived from its properties. */
export type FileState =
  /** A pending upload, whose signed FieldValue is submitted. */
  | { kind: 'pending'; fieldValue: string; fileName: string }
  /** The existing file is cleared, by submitting the clear value. */
  | { kind: 'cleared' }
  /** The existing file is kept, by submitting nothing; its info may be absent. */
  | { kind: 'kept'; fileName: string; fileUrl: string }
  /** No file, so nothing is submitted. */
  | { kind: 'none' };

export interface FileStateInputs {
  value: string;
  hasExistingFile: boolean;
  fileName: string;
  fileUrl: string;
  uploadedFileName: string;
}

export function deriveFileState(inputs: FileStateInputs): FileState {
  if (inputs.value === CLEAR_VALUE) {
    return { kind: 'cleared' };
  }
  if (inputs.value) {
    return {
      kind: 'pending',
      fieldValue: inputs.value,
      // A server-rendered pending value provides its file name as the represented one
      fileName: inputs.uploadedFileName || inputs.fileName,
    };
  }
  if (inputs.hasExistingFile) {
    return { kind: 'kept', fileName: inputs.fileName, fileUrl: inputs.fileUrl };
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
 * The server doesn't state this directly; it follows from how each case is rendered:
 * - a kept existing file has its info rendered, with no value;
 * - a pending upload has its value rendered, with that upload's own file info (in place of any
 *   existing file's, which is then unknown);
 * - a clear has the clear value rendered alone, and only an existing file can be cleared.
 */
export function hasExistingFile(inputs: { value: string; fileName: string }): boolean {
  if (inputs.value === CLEAR_VALUE) {
    return true;
  }
  if (inputs.value) {
    return false;
  }
  return Boolean(inputs.fileName);
}
