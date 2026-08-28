import './style.scss';
import S3FileInput from './S3FileInput.js';

function attachToFileInputs(): void {
  for (const element of document.querySelectorAll<HTMLInputElement>('input[data-s3fileinput]')) {
    // biome-ignore lint/correctness/noUnusedInstantiation: intentional design
    new S3FileInput(element);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', attachToFileInputs.bind(this));
} else {
  attachToFileInputs();
}
