import './imagestyle.scss';
import S3ImageInput from './S3ImageInput.js';

function attachToImageInputs(): void {
  for (const element of document.querySelectorAll<HTMLInputElement>('input[data-s3fileinput]')) {
    new S3ImageInput(element);
  }
}

if (document.readyState !== 'loading') {
  attachToImageInputs();
} else {
  document.addEventListener('DOMContentLoaded', attachToImageInputs.bind(this));
}
