import {DEFAULT_BASE_URL, EVENT_UPLOAD_COMPLETE, EVENT_UPLOAD_STARTED} from "./constants";
import {FileUploader, Progress, ProgressState, UploadResult} from "./uploader";

function cssClass(clazz: string): string {
  return `s3fileinput-${clazz}`;
}

function sized(val: number): string {
  const units = ["bytes", "KiB", "MiB", "GiB", "TiB"];
  const factor = 1024;
  let v = val;
  while (v > factor && units.length > 0) {
    v /= factor;
    units.shift();
  }
  return `${Math.round(v * 100) / 100}${units[0]}`;
}

export interface S3FileInputOptions {
  /**
   * @default /api/joist
   */
  baseUrl: string;
  /**
   * @default false
   */
  autoUpload: boolean;
}

function i18n(text: string): string {
  return text;
}

export default class S3FileInput {
  private readonly node: HTMLElement;
  private readonly input: HTMLInputElement;
  private readonly info: HTMLElement;
  private readonly uploadButton: HTMLButtonElement;
  private readonly abortButton: HTMLButtonElement;
  private readonly clearButton: HTMLButtonElement;
  private readonly spinnerWrapper: HTMLElement;

  private readonly baseUrl: string;
  private readonly autoUpload: boolean;

  constructor(input: HTMLInputElement, options: Partial<S3FileInputOptions> = {}) {
    this.input = input;

    this.baseUrl =
      options.baseUrl || this.input.dataset.s3fileinput || DEFAULT_BASE_URL;
    this.autoUpload =
      options.autoUpload != null
        ? options.autoUpload
        : this.input.dataset.autoUpload != null;

    this.node = input.ownerDocument!.createElement("div");
    this.node.classList.add(cssClass("wrapper"));
    this.node.innerHTML = `<div class="${cssClass("inner")}">
    <div class="${cssClass("info")}"></div>
    <button type="button" class="${cssClass("upload")}" disabled>
      ${i18n("Upload to S3")}
    </button>
    <button type="button" class="${cssClass("abort")}" title="${i18n('Abort Upload')}">
      ${i18n("Abort")}
    </button>
    <button type="button" class="${cssClass("clear")}" title="${i18n('Clear (file was already uploaded tho)')}">
      ${i18n("x")}
    </button>
    <div class="${cssClass("spinner-wrapper")}">
      <div class="${cssClass(
        "spinner"
      )}"><div></div><div></div><div></div><div></div>
    </div>
  </div>`;
    this.input.parentElement!.replaceChild(this.node, this.input);
    this.uploadButton = this.node.querySelector<HTMLButtonElement>(
      `.${cssClass("upload")}`
    )!;
    this.clearButton = this.node.querySelector<HTMLButtonElement>(
      `.${cssClass("clear")}`
    )!;
    this.info = this.node.querySelector<HTMLElement>(
      `.${cssClass("info")}`
    )!;
    if (this.autoUpload) {
      this.uploadButton.classList.add(cssClass('autoupload'));
    }
    this.uploadButton.insertAdjacentElement("beforebegin", this.input);
    this.abortButton = this.node.querySelector<HTMLButtonElement>(
      `.${cssClass("abort")}`
    )!;
    this.spinnerWrapper = this.node.querySelector<HTMLElement>(
      `.${cssClass("spinner-wrapper")}`
    )!;


    this.input.onchange = (evt): void => {
      evt.preventDefault();
      if (this.input.type === "file") {
        const files = Array.from(this.input.files || []);
        this.handleFiles(files);
      } else if (this.input.value === "") {
        // already processed but user resetted it -> convert bak
        this.input.type = "file";
        this.info.innerText = "";
        this.node.classList.remove(cssClass("set"));
      }
    };

    this.clearButton.onclick = (evt): void => {
      evt.preventDefault();
      evt.stopPropagation();
      this.input.type = "file";
      this.input.value = "";
      this.info.innerText = "";
      this.node.classList.remove(cssClass("set"));
    }

    this.uploadButton.onclick = (evt): void => {
      evt.preventDefault();
      evt.stopPropagation();
      this.uploadFiles();
    };
  }

  private handleFiles(files: File[]): void | Promise<void> {
    if (this.autoUpload) {
      return this.uploadFiles();
    }
    this.uploadButton.disabled = files.length === 0;

    this.input.setCustomValidity(
      files.length > 0 ? i18n("Press Upload Button to upload directly") : ""
    );
  }

  private onUploadProgress(p: Progress) {
    progress.dataset.state = p.state;
    indicator.style.width = `${Math.round(p.percentage * 100)}%`;
    progress.title = {
      [ProgressState.Initializing]: `${file.name}: ${i18n('Initializing Upload')}`,
      [ProgressState.Preparing]: `${file.name}: ${i18n('Requesting Upload Token')}`,
      [ProgressState.Uploading]: `${file.name}: ${Math.round(
          (100 * p.loaded) / p.total
        )}% ${sized(p.loaded)}/${sized(p.total)}`,
      [ProgressState.Finishing]: `${file.name}: ${i18n('Finishing Upload')}`,
      [ProgressState.Done]: `${file.name}: ${i18n('Done ')} (${sized(p.total)})`,
      [ProgressState.Aborting]: `${file.name}: ${i18n('Aborting Upload')}`,
      [ProgressState.Aborted]: `${file.name}: ${i18n('Upload Aborted')}`,
    }[p.state];
  }

  private async uploadFile(file: File): Promise<UploadResult> {
    const progress = this.node.ownerDocument!.createElement("div");
    progress.classList.add(cssClass("progress"));
    const indicator = this.node.ownerDocument!.createElement("div");
    progress.appendChild(indicator);
    this.node.appendChild(progress);

    this.input.dispatchEvent(new CustomEvent(EVENT_UPLOAD_STARTED, {
      detail: file
    }));

    const onProgress = (p: Progress): void => {
      // progress.dataset.state = p.state;
      indicator.style.width = `${Math.round(p.percentage * 100)}%`;
      progress.title = {
        [ProgressState.Initializing]: `${file.name}: ${i18n('Initializing Upload')}`,
        [ProgressState.Preparing]: `${file.name}: ${i18n('Requesting Upload Token')}`,
        [ProgressState.Uploading]:
            `${file.name}: ${Math.round((100 * p.percentage) / file.size)}% ${sized(p.percentage * file.size)}/${sized(file.size)}`,
        // [ProgressState.Uploading]: `${file.name}: ${Math.round(
        //     (100 * p.percentage) / file.size
        //   )}% ${sized(p.percentage * file.size)}/${sized(file.size)}`,
        [ProgressState.Finishing]: `${file.name}: ${i18n('Finishing Upload')}`,
        [ProgressState.Done]: `${file.name}: ${i18n('Done ')} (${sized(file.size)})`,
        [ProgressState.Aborting]: `${file.name}: ${i18n('Aborting Upload')}`,
        [ProgressState.Aborted]: `${file.name}: ${i18n('Upload Aborted')}`,
      }[p.state];
    };

    const fileUploader = new FileUploader(file, this.baseUrl, onProgress);
    const abortHandler = (evt: MouseEvent): void => {
      evt.preventDefault();
      fileUploader.abort();
    };
    this.abortButton.addEventListener("click", abortHandler);
    try {
      const r = await fileUploader.upload()
    } catch (e) {
      if (e.name === 'AbortError') {
        progress.title = `${file.name}: ${i18n('Upload Aborted')}`;
      } else {
        progress.title = `${file.name}: ${i18n("Error occurred")}: ${e}`;
      }
    }
    this.abortButton.removeEventListener("click", abortHandler);

    progress.dataset.state = r.state;
    progress.title = `${file.name}: ${i18n('Done')} (${sized(file.size)})`;
    this.input.dispatchEvent(new CustomEvent(EVENT_UPLOAD_COMPLETE, {
      detail: r
    }));
    // progress.remove();
    return r;
  }

  private uploadFiles(): Promise<void> | void {
    const files = Array.from(this.input.files || []);
    if (files.length === 0) {
      return;
    }

    const bb = this.input.getBoundingClientRect();
    this.spinnerWrapper.style.width = `${bb.width}px`;
    this.spinnerWrapper.style.height = `${bb.height}px`;

    this.node.classList.add(cssClass("uploading"));
    this.uploadButton.disabled = true;
    this.input.setCustomValidity(i18n("Uploading files, wait till finished"));
    this.input.value = ""; // reset file selection

    const file = files[0];

    return this.uploadFile(file).then(result => {
      this.node.classList.remove(cssClass("uploading"));
      if (result.state === "successful") {
        this.node.classList.add(cssClass("set"));
        this.input.setCustomValidity(""); // no error
        this.input.type = "hidden";
        this.input.value = result.value;
        this.info.innerText = file.name;
      }
    });
  }
}
