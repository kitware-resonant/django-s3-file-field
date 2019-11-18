import './style.scss';
import { DEFAULT_BASE_URL } from './constants';
import { uploadFile } from './uploader';

function cssClass(clazz: string) {
  return `s3fileinput-${clazz}`;
}

export default class S3FileInput {
  private readonly node: HTMLElement;
  private readonly input: HTMLInputElement;
  private readonly uploadButton: HTMLButtonElement;

  private readonly baseUrl: string;

  constructor(node: HTMLElement) {
    this.node = node;
    this.input = node.querySelector('input')!;
    this.uploadButton = node.querySelector('button')!;

    this.baseUrl = this.node.dataset.baseurl || DEFAULT_BASE_URL;

    this.input.onchange = (evt) => {
      evt.preventDefault();
      const files = Array.from(this.input.files || []);
      this.handleFiles(files);
    };

    this.uploadButton.onclick = (evt) => {
      evt.preventDefault();
      evt.stopPropagation();
      this.uploadFiles(Array.from(this.input.files || []));
    }
  }

  private handleFiles(files: File[]) {
    this.uploadButton.disabled = files.length === 0;
  }

  private async uploadFile(file: File) {
    const progress = this.node.ownerDocument!.createElement('progress');
    this.node.appendChild(progress);

    try {
      return await uploadFile(file, {
        baseUrl: this.baseUrl,
        onProgress: (({ percentage }) => {
          progress.value = Math.round(percentage * 100)
        })
      });
    } finally {
      progress.remove();
    }
  }

  private uploadFiles(files: File[]) {
    this.node.classList.add(cssClass('uploading'));
    this.uploadButton.disabled = true;
    this.input.setCustomValidity('Uploading files, wait till finished');


    // prepare n progress bars
    // one by or or multi??
    Promise.all(files.map((f) => this.uploadFile(f))).then(() => {
      this.node.classList.remove(cssClass('uploading'));
    });
  }
}
