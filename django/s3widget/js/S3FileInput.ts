import './style.scss';
import { DEFAULT_BASE_URL } from './constants';
import { uploadFile } from './uploader';

function cssClass(clazz: string) {
  return `s3fileinput-${clazz}`;
}

function sized(val: number) {
  const units = ['bytes', 'KiB', 'MiB', 'GiB', 'TiB'];
  const factor = 1024;
  let v = val;
  while (v > factor && units.length > 0) {
    v /= factor;
    units.shift();
  }
  return `${Math.round(v * 100) / 100}${units[0]}`;
}

export default class S3FileInput {
  private readonly node: HTMLElement;
  private readonly input: HTMLInputElement;
  private readonly uploadButton: HTMLButtonElement;
  private readonly abortButton: HTMLButtonElement;
  private readonly spinnerWrapper: HTMLElement;

  private readonly baseUrl: string;

  constructor(node: HTMLElement) {
    this.node = node;
    this.input = node.querySelector('input')!;
    this.uploadButton = node.querySelector<HTMLButtonElement>(`.${cssClass('upload')}`)!;
    this.uploadButton.insertAdjacentHTML('afterend', `<button type="button" class="s3fileinput-abort">Abort</button>`);
    this.abortButton = node.querySelector<HTMLButtonElement>(`.${cssClass('abort')}`)!;
    this.abortButton.insertAdjacentHTML('afterend', `<div class="${cssClass('spinner-wrapper')}">
      <div class="${cssClass('spinner')}"><div></div><div></div><div></div><div></div>
    </div>`);
    this.spinnerWrapper = node.querySelector<HTMLElement>(`.${cssClass('spinner-wrapper')}`)!;

    this.baseUrl = this.node.dataset.baseurl || DEFAULT_BASE_URL;

    this.input.onchange = (evt) => {
      evt.preventDefault();
      const files = Array.from(this.input.files || []);
      this.handleFiles(files);
    };

    this.uploadButton.onclick = (evt) => {
      evt.preventDefault();
      evt.stopPropagation();
      this.uploadFiles();
    }
  }

  private handleFiles(files: File[]) {
    this.uploadButton.disabled = files.length === 0;

    this.input.setCustomValidity(files.length > 0 ? 'Press Upload Button to upload directly' : '');
  }

  private uploadFile(file: File) {
    const progress = this.node.ownerDocument!.createElement('div');
    progress.classList.add(cssClass('progress'));
    const indicator = this.node.ownerDocument!.createElement('div');
    progress.appendChild(indicator);
    this.node.appendChild(progress);

    let abortHandler: null | ((evt: MouseEvent) => void) = null;

    return uploadFile(file, {
      baseUrl: this.baseUrl,
      onProgress: (p) => {
        progress.dataset.state = p.state;
        indicator.style.width = `${Math.round(p.percentage * 100)}%`;
        switch (p.state) {
          case 'initial':
            progress.title = `${file.name}: Initializing Upload`;
            break;
          case 'preparing':
            progress.title = `${file.name}: Requesting Upload Token`;
            break;
          case 'uploading':
            progress.title = `${file.name}: ${Math.round(100 * p.loaded / p.total)}% ${sized(p.loaded)}/${sized(p.total)}`;
            break;
          case 'finishing':
            progress.title = `${file.name}: Finishing Upload`;
            break;
          case 'aborted':
            progress.title = `${file.name}: Upload Aborted`;
            break;
          case 'done':
            progress.title = `${file.name}: Done (${sized(p.total)})`;
            break;
        }
      },
      abortSignal: (onAbort) => {
        abortHandler = (evt) => {
          evt.preventDefault();
          onAbort();
        };
        this.abortButton.addEventListener('click', abortHandler);
      }
    }).then((r) => {
      if (abortHandler) {
        this.abortButton.removeEventListener('click', abortHandler);
      }
      progress.dataset.state = r.state;
      switch (r.state) {
        case 'successful':
          progress.title = `${file.name}: Done (${sized(file.size)})`;
          break;
        case 'aborted':
          progress.title = `${file.name}: Upload Aborted`;
          break;
        case 'error':
          progress.title = `${file.name}: Error occurred: ${r.msg}`;
          break;
      }
      // progress.remove();
      return r;
    });
  }

  private uploadFiles() {
    const files = Array.from(this.input.files || []);
    if (files.length === 0) {
      return;
    }

    const bb = this.input.getBoundingClientRect();
    this.spinnerWrapper.style.width = `${bb.width}px`;
    this.spinnerWrapper.style.height = `${bb.height}px`;

    this.node.classList.add(cssClass('uploading'));
    this.uploadButton.disabled = true;
    this.input.setCustomValidity('Uploading files, wait till finished');
    this.input.value = ''; // reset file selection

    // prepare n progress bars
    // one by or or multi??
    Promise.all(files.map((f) => this.uploadFile(f))).then(() => {
      this.node.classList.remove(cssClass('uploading'));
      this.input.setCustomValidity('');
    });
  }
}
