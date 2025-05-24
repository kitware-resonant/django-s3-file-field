import './style.scss';
import S3FileInput from './S3FileInput.js';

function attachToFileInputs(): void {
  document.querySelectorAll<HTMLInputElement>('input[data-s3fileinput]').forEach((element) => {
    new S3FileInput(element);
  });
}

if (document.readyState !== 'loading') {
  attachToFileInputs();
} else {
  document.addEventListener('DOMContentLoaded', attachToFileInputs.bind(this));
}
