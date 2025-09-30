import './style.scss';
import S3FileInput from './S3FileInput.js';

function attachToFileInputs(): void {
  for (const element of document.querySelectorAll<HTMLInputElement>('input[data-s3fileinput]')) {
    new S3FileInput(element);
  }
}

if (document.readyState !== 'loading') {
  attachToFileInputs();
} else {
  document.addEventListener('DOMContentLoaded', attachToFileInputs.bind(this));
}

window.S3FileInput = S3FileInput;
