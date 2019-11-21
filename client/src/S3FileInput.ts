import "./style.scss";
import { DEFAULT_BASE_URL, EVENT_UPLOAD_COMPLETE, EVENT_UPLOAD_STARTED } from "./constants";
import { uploadFile, UploadResult } from "./uploader";

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

function fileInfo(result: UploadResult, file: File): string {
  return JSON.stringify({
    name: result.name,
    size: file.size,
    id: result.id
  });
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

  private uploadFile(file: File): Promise<UploadResult> {
    const progress = this.node.ownerDocument!.createElement("div");
    progress.classList.add(cssClass("progress"));
    const indicator = this.node.ownerDocument!.createElement("div");
    progress.appendChild(indicator);
    this.node.appendChild(progress);

    let abortHandler: null | ((evt: MouseEvent) => void) = null;

    const event = new CustomEvent(EVENT_UPLOAD_STARTED, {
      detail: file
    });
    this.input.dispatchEvent(event);

    return uploadFile(file, {
      baseUrl: this.baseUrl,
      onProgress: p => {
        progress.dataset.state = p.state;
        indicator.style.width = `${Math.round(p.percentage * 100)}%`;
        switch (p.state) {
          case "initial":
            progress.title = `${file.name}: ${i18n('Initializing Upload')}`;
            break;
          case "preparing":
            progress.title = `${file.name}: ${i18n('Requesting Upload Token')}`;
            break;
          case "uploading":
            progress.title = `${file.name}: ${Math.round(
              (100 * p.loaded) / p.total
            )}% ${sized(p.loaded)}/${sized(p.total)}`;
            break;
          case "finishing":
            progress.title = `${file.name}: ${i18n('Finishing Upload')}`;
            break;
          case "aborted":
            progress.title = `${file.name}: ${i18n('Upload Aborted')}`;
            break;
          case "done":
            progress.title = `${file.name}: ${i18n('Done ')} (${sized(p.total)})`;
            break;
        }
      },
      abortSignal: onAbort => {
        abortHandler = (evt): void => {
          evt.preventDefault();
          onAbort();
        };
        this.abortButton.addEventListener("click", abortHandler);
      }
    }).then(r => {
      if (abortHandler) {
        this.abortButton.removeEventListener("click", abortHandler);
      }
      progress.dataset.state = r.state;
      const event = new CustomEvent(EVENT_UPLOAD_COMPLETE, {
        detail: r
      });
      this.input.dispatchEvent(event);
      switch (r.state) {
        case "successful":
          progress.title = `${file.name}: ${i18n('Done')} (${sized(file.size)})`;
          break;
        case "aborted":
          progress.title = `${file.name}: ${i18n('Upload Aborted')}`;
          break;
        case "error":
          progress.title = `${file.name}: ${i18n("Error occurred")}: ${r.msg}`;
          break;
      }
      // progress.remove();
      return r;
    });
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
        this.input.value = fileInfo(result, file);
        this.info.innerText = file.name;
      }
    });
  }
}
