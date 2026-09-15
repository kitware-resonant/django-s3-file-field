/** The state of the file the element represents, derived from its properties. */
export type FileState =
  /** A pending upload, whose signed FieldValue is submitted. */
  | { kind: 'pending'; fieldValue: string; fileName: string }
  /** The existing file is cleared, by submitting an empty value. */
  | { kind: 'cleared' }
  /** The existing file is kept, by submitting nothing; its info may be absent. */
  | { kind: 'kept'; fileName: string; fileUrl: string }
  /** No file, so nothing is submitted. */
  | { kind: 'none' };

export interface FileStateInputs {
  value: string;
  cleared: boolean;
  hasExistingFile: boolean;
  fileName: string;
  fileUrl: string;
  uploadedFileName: string;
}

export function deriveFileState(inputs: FileStateInputs): FileState {
  if (inputs.value) {
    return {
      kind: 'pending',
      fieldValue: inputs.value,
      // A server-rendered pending value provides its file name as the represented one
      fileName: inputs.uploadedFileName || inputs.fileName,
    };
  }
  if (inputs.cleared) {
    return { kind: 'cleared' };
  }
  if (inputs.hasExistingFile) {
    return { kind: 'kept', fileName: inputs.fileName, fileUrl: inputs.fileUrl };
  }
  return { kind: 'none' };
}

/** The form value to submit for a file state: a value, an explicit empty value, or omission. */
export function formValueFor(fileState: FileState): string | null {
  switch (fileState.kind) {
    case 'pending':
      return fileState.fieldValue;
    case 'cleared':
      return '';
    default:
      return null;
  }
}

/** Whether the server-rendered properties represent an existing (already saved) file. */
export function hasExistingFile(inputs: {
  value: string;
  cleared: boolean;
  fileName: string;
}): boolean {
  // An existing file is represented either by its info (without a pending value eclipsing it)
  // or by a server-rendered cleared state (which omits its info)
  return (Boolean(inputs.fileName) && !inputs.value) || inputs.cleared;
}
