export { default } from './S3FileInput';
export * from './S3FileInput';

import S3FileInput from './S3FileInput';

export function autoInit(): void {
  // auto init
  const wrappers = Array.from(document.querySelectorAll<HTMLInputElement>('input[data-s3fileinput]'));
  wrappers.forEach((w) => new S3FileInput(w));
}

if (document.readyState != 'loading') {
  autoInit();
} else {
  document.addEventListener('DOMContentLoaded', autoInit);
}
