// biome-ignore-all lint/suspicious/noUnnecessaryConditions: reactive properties are externally assigned by Lit, invisibly to type inference

import type { S3FileFieldProgress } from 'django-s3-file-field';
import { css, html, LitElement, nothing, type PropertyValues, svg, type TemplateResult } from 'lit';
import { customElement, property, query, state } from 'lit/decorators.js';
import { classMap } from 'lit/directives/class-map.js';
import prettyBytes from 'pretty-bytes';
import {
  CLEAR_VALUE,
  deriveFileState,
  type FileState,
  formValueFor,
  hasExistingFile,
} from './state.js';
import { uploadFile } from './upload.js';

/**
 * The state which determines the submission, as changed by the user.
 *
 * This is restored on form reset, and by the browser (as on navigating back to the page).
 */
interface RestorableState {
  value: string;
  uploadedFileName: string;
}

function formatBytes(bytes: number): string {
  return prettyBytes(bytes, { binary: true });
}

const uploadIcon = svg`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/></svg>`;
const fileIcon = svg`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z"/><path d="M14 3v5h5"/></svg>`;
const removeIcon = svg`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>`;

/**
 * A form-associated custom element, uploading a file directly to S3 for an S3FileField.
 *
 * The API is expressed as properties, which may also be set as HTML attributes, so the element
 * can be server-rendered by Django or driven by a frontend framework. The "value" is what is
 * submitted: after an upload, its signed FieldValue; on removing an existing file, the clear
 * value; otherwise, it is empty and nothing is submitted, which keeps any existing file. An
 * "input" event is fired when the user changes it, so a framework may bind it (as with v-model).
 *
 * The element inherits the page's font and text color, from which its borders and fills are
 * derived. Its accent color, error color and corner radius are read from the page's theme
 * (DaisyUI's or Vuetify's variables), or may be set with the "--s3-file-input-*" properties.
 */
@customElement('s3-file-input')
export class S3FileInputElement extends LitElement {
  // Participate in form submission directly, via ElementInternals
  static readonly formAssociated = true;

  static override readonly shadowRootOptions = {
    ...LitElement.shadowRootOptions,
    delegatesFocus: true,
  };

  static override readonly styles = css`
    :host {
      --_accent: var(
        --s3-file-input-accent-color,
        var(--color-primary, rgb(var(--v-theme-primary, 24, 103, 192)))
      );
      --_error: var(
        --s3-file-input-error-color,
        var(--color-error, rgb(var(--v-theme-error, 176, 0, 32)))
      );
      --_radius: var(--s3-file-input-radius, var(--radius-field, 0.25rem));
      --_line: color-mix(in oklab, currentColor 30%, transparent);
      --_fill: color-mix(in oklab, currentColor 6%, transparent);
      --_muted: color-mix(in oklab, currentColor 60%, transparent);
      /* A theme's error color may be tuned for backgrounds; as text, pull it toward the text color */
      --_error-text: color-mix(in oklab, var(--_error) 65%, currentColor);

      /* Custom elements are inline by default; a sized inline-level box keeps the element in flow
         beside a form label, like a native input */
      display: inline-block;
      box-sizing: border-box;
      /* Form controls set their own text size rather than inheriting it: native inputs use the
         browser's control size (about 13px), DaisyUI's fields 14px, Vuetify's 16px. Inheriting
         would size the widget by the surrounding text, which in a DaisyUI fieldset is a 12px
         label. So set DaisyUI's, which is close to native; the page may still override it. The
         font family is inherited, and the internal geometry is in em, so it scales with this. */
      font-size: 0.875rem;
      /* In rem, so the width matches framework fields (as DaisyUI's) at any text size */
      width: 20rem;
      max-width: 100%;
      vertical-align: middle;
    }

    :host(:disabled) .field {
      opacity: 0.5;
    }

    svg {
      flex: none;
      width: 1.25em;
      height: 1.25em;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    a {
      color: inherit;
      text-underline-offset: 2px;
    }

    button {
      all: unset;
      box-sizing: border-box;
      cursor: pointer;
    }

    button:focus-visible,
    .choose:has(.picker:focus-visible) {
      outline: 2px solid var(--_accent);
      outline-offset: 2px;
    }

    .field {
      position: relative;
      box-sizing: border-box;
      display: flex;
      align-items: center;
      gap: 0.5em;
      min-height: 3.5em;
      padding-right: 0.375em;
      border: 1px solid var(--_line);
      border-radius: var(--_radius);
      overflow: hidden;
    }

    .field.error {
      border-color: var(--_error);
    }

    .field.dragging {
      border-style: dashed;
      border-color: var(--_accent);
      background: color-mix(in oklab, var(--_accent) 8%, transparent);
      color: var(--_accent);
    }

    /* The picker itself is not shown; its label is the "Choose file" segment */
    .choose {
      position: relative;
      align-self: stretch;
      display: flex;
      align-items: center;
      gap: 0.5em;
      padding: 0 0.875em;
      margin-right: 0.25em;
      font-weight: 600;
      background: var(--_fill);
      border-right: 1px solid var(--_line);
      cursor: pointer;
    }

    .choose:hover {
      background: color-mix(in oklab, currentColor 10%, transparent);
    }

    .picker {
      /* Keep it over its label, so the browser's validation message points there */
      position: absolute;
      inset: 0;
      opacity: 0;
      pointer-events: none;
    }

    .lead {
      display: flex;
      margin-left: 0.75em;
      color: var(--_muted);
    }

    .dragging .lead {
      color: inherit;
    }

    .text {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
      min-width: 0;
      padding: 0.375em 0;
      line-height: 1.3;
    }

    .primary,
    .status {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .status {
      font-size: 0.8125em;
      color: var(--_muted);
    }

    /* Without a primary line, the status is the only one, so give it the primary's size */
    .primary:empty {
      display: none;
    }

    .primary:empty + .status {
      font-size: inherit;
      white-space: normal;
    }

    .error .status {
      color: var(--_error-text);
    }

    .dragging .status {
      color: inherit;
      opacity: 0.8;
    }

    .muted {
      color: var(--_muted);
    }

    .percent {
      padding-right: 0.5em;
      font-size: 0.8125em;
      font-variant-numeric: tabular-nums;
      color: var(--_muted);
    }

    .remove {
      display: grid;
      place-items: center;
      flex: none;
      width: 2em;
      height: 2em;
      border-radius: 50%;
      color: var(--_muted);
    }

    .remove svg {
      width: 1.125em;
      height: 1.125em;
    }

    /* Filled like the "Choose file" segment, so it reads as an action rather than status */
    .undo {
      padding: 0.35em 0.75em;
      font-weight: 600;
      background: var(--_fill);
      border-radius: var(--_radius);
    }

    .remove:hover {
      background: var(--_fill);
    }

    .undo:hover {
      background: color-mix(in oklab, currentColor 10%, transparent);
    }

    /* A thin line along the bottom edge of the field */
    progress {
      position: absolute;
      inset: auto 0 0 0;
      width: 100%;
      height: 3px;
      border: 0;
      appearance: none;
      background: var(--_fill);
      color: var(--_accent);
    }

    progress::-webkit-progress-bar {
      background: transparent;
    }

    progress::-webkit-progress-value {
      background: var(--_accent);
    }

    progress::-moz-progress-bar {
      background: var(--_accent);
    }
  `;

  /** The base URL of the upload API. */
  @property({ attribute: 'base-url' })
  accessor baseUrl = '';

  /** The identifier of the S3FileField to upload to. */
  @property({ attribute: 'field-id' })
  accessor fieldId = '';

  /** The maximum file size. */
  @property({ attribute: 'max-size', type: Number })
  accessor maxSize: number | undefined;

  /**
   * The value to submit: empty to keep any existing file, the clear value to remove it, or a
   * pending upload's signed FieldValue.
   *
   * This may be server-rendered (on form redisplay) or set by the user; "existingUrl"
   * describes the represented file, for display. An empty value is always a string
   * (never null or undefined), which frameworks may rely on.
   */
  @property()
  accessor value = '';

  /**
   * Whether the field is disabled, so no controls are rendered.
   *
   * This reflects to the "disabled" attribute, which the browser honors for form submission.
   * A disabled ancestor fieldset also disables the field, but without setting this (see
   * "formDisabled").
   */
  @property({ type: Boolean, reflect: true })
  accessor disabled = false;

  /**
   * Whether a file is required, so the element is invalid without one.
   *
   * Unlike a native file input, an existing file satisfies this (until it is removed), so Django
   * renders it on edit forms too.
   */
  @property({ type: Boolean })
  accessor required = false;

  /**
   * The URL of the existing (saved) file; best-effort, display-only.
   *
   * The file is linked to, and named by the final component of the URL's path. On a redisplay
   * of a pending upload, Django gives that upload's storage key instead, which only names it,
   * as an unvalidated upload is never linked to.
   */
  @property({ attribute: 'existing-url' })
  accessor existingUrl = '';

  /**
   * Whether the browser considers the field disabled, for any reason (including an ancestor
   * fieldset), as reported by "formDisabledCallback".
   *
   * This is deliberately kept apart from "disabled": reflecting it there would pin a "disabled"
   * attribute onto the element, which would then outlast the fieldset's own disabling.
   */
  @state()
  accessor formDisabled = false;

  /** The file being uploaded, while one is. */
  @state()
  accessor uploadingFile: File | undefined;

  /** The progress of the upload, as reported by the client; its byte counts are only present
   * while the file content is transferring, so the bar is indeterminate around that. */
  @state()
  accessor uploadProgress: S3FileFieldProgress | undefined;

  /** The local name of an uploaded file; empty for a server-rendered pending value. */
  @state()
  accessor uploadedFileName = '';

  @state()
  accessor errorMessage = '';

  /** Whether a file is being dragged over the element, when it can accept one. */
  @state()
  accessor dragging = false;

  /** The file picker, which is only rendered when a file can be chosen; assigned by the decorator. */
  @query('#picker')
  accessor picker!: HTMLInputElement | null;

  /** The first control (rather than a link in the text), to receive restored focus. */
  @query('.field :is(input, button):not(:disabled)')
  accessor firstControl!: HTMLElement | null;

  /** The status line, which is always rendered; assigned by the decorator. */
  @query('.status')
  accessor status!: HTMLElement | null;

  private readonly internals = this.attachInternals();

  /** The server-rendered state, captured on connection, to which a form reset returns. */
  private initial: RestorableState = { value: '', uploadedFileName: '' };

  /**
   * Whether an existing (already saved) file is known of, from the server-rendered properties;
   * it is then kept or cleared, and the user can't make it unknown.
   */
  private existingFileKnown = false;

  /** The associated form, whose submission is guarded while uploading. */
  private form: HTMLFormElement | null = null;

  /** Whether focus was within the element before an update, and is to be restored after it. */
  private restoreFocus = false;

  constructor() {
    super();
    // The host is what the form's label names, so expose it as a named group of its controls
    this.internals.role = 'group';
    // Drag events from the shadow tree are retargeted to the host, and the browser doesn't
    // dispatch "dragenter" or "dragleave" here when moving between its own children, so these
    // fire only on entering and leaving the element as a whole
    this.addEventListener('dragenter', this.handleDragOver);
    this.addEventListener('dragover', this.handleDragOver);
    this.addEventListener('dragleave', this.handleDragLeave);
    this.addEventListener('drop', this.handleDrop);
    this.addEventListener('click', this.handleHostClick);
  }

  override connectedCallback(): void {
    super.connectedCallback();
    if (!this.hasUpdated) {
      // Capture the state as server-rendered, before the user can change it; a later
      // reconnection (as when the element is moved) must not recapture it
      this.initial = this.restorableState;
      this.existingFileKnown = hasExistingFile({
        ...this.initial,
        existingUrl: this.existingUrl ?? '',
      });
    }
  }

  override willUpdate(changedProperties: PropertyValues<this>): void {
    this.restoreFocus ||= this.matches(':focus-within');
    if (changedProperties.has('existingUrl')) {
      // The URL may be set after connection (as by an app, once it has fetched the resource),
      // so what it represents is re-evaluated whenever it changes
      this.existingFileKnown = hasExistingFile({
        value: this.value ?? '',
        existingUrl: this.existingUrl ?? '',
      });
    }
  }

  override updated(): void {
    // The form value and validity derive from several properties, so they are synced after every
    // update, rather than in setters
    const fileState = this.fileState;
    this.internals.setFormValue(formValueFor(fileState), JSON.stringify(this.restorableState));
    this.syncValidity(fileState);
    this.syncFocus();
  }

  private syncValidity(fileState: FileState): void {
    // The browser shows a validity message only on a focusable anchor
    if (this.uploading) {
      // No control is rendered while uploading, so the status (which is focusable by script for
      // this alone) anchors the message instead
      const anchor = this.status ?? undefined;
      this.internals.setValidity({ customError: true }, 'Upload in progress.', anchor);
    } else if (this.required && (fileState.kind === 'none' || fileState.kind === 'cleared')) {
      const anchor = this.picker ?? undefined;
      this.internals.setValidity({ valueMissing: true }, 'Please select a file.', anchor);
    } else {
      this.internals.setValidity({});
    }
  }

  /**
   * Restore focus to the first control, if an update removed the focused control.
   *
   * As when an upload replaces the picker with "Remove"; focus would otherwise drop to the
   * document.
   */
  private syncFocus(): void {
    if (this.restoreFocus && this.focusDropped) {
      // If there is no control (as while uploading), this remains to be restored by a later update
      this.firstControl?.focus();
    }
    // Focus on a disabled control doesn't count, as the browser is about to drop it
    this.restoreFocus &&= !this.renderRoot.querySelector(':focus:not(:disabled)');
  }

  formAssociatedCallback(form: HTMLFormElement | null): void {
    this.form?.removeEventListener('submit', this.handleFormSubmit);
    this.form = form;
    this.form?.addEventListener('submit', this.handleFormSubmit);
  }

  async formDisabledCallback(disabled: boolean): Promise<void> {
    // When this is caused by reflecting "disabled" to the attribute, it fires within an update,
    // after rendering, where a property change would be lost; so apply it after the update
    await this.updateComplete;
    this.formDisabled = disabled;
  }

  formStateRestoreCallback(formState: File | string | FormData | null, mode: string): void {
    // Only the state given to "setFormValue" is restored; autocompletion is meaningless for a file
    if (mode !== 'restore' || typeof formState !== 'string') {
      return;
    }
    this.restorableState = JSON.parse(formState) as RestorableState;
  }

  formResetCallback(): void {
    if (this.uploading) {
      // The upload would otherwise land after the reset, resurrecting a value the user believed
      // to be discarded; instead, it is kept, and may be removed once it completes
      return;
    }
    this.resetPicker();
    this.restorableState = this.initial;
    this.errorMessage = '';
  }

  private get restorableState(): RestorableState {
    // The string properties may be set to null or undefined (e.g. by removing an attribute, or
    // by a framework binding), which is equivalent to empty
    return {
      value: this.value ?? '',
      uploadedFileName: this.uploadedFileName,
    };
  }

  private set restorableState(restorableState: RestorableState) {
    this.value = restorableState.value;
    this.uploadedFileName = restorableState.uploadedFileName;
  }

  /** Announce a change of the value by the user, as a native input does. */
  private dispatchInput(): void {
    this.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
  }

  /** Whether the field is disabled, by its own property or by the browser. */
  private get isDisabled(): boolean {
    return this.disabled || this.formDisabled;
  }

  private get uploading(): boolean {
    return this.uploadingFile !== undefined;
  }

  /** Whether nothing is focused, in the element's own tree; as after a focused node is removed. */
  private get focusDropped(): boolean {
    const active = (this.getRootNode() as Document | ShadowRoot).activeElement;
    return active === null || active === document.body;
  }

  private get fileState(): FileState {
    return deriveFileState({
      ...this.restorableState,
      existingFileKnown: this.existingFileKnown,
      existingUrl: this.existingUrl ?? '',
    });
  }

  /** Whether a file can be chosen or dropped, in the current state. */
  private canPick(fileState: FileState): boolean {
    return (
      !(this.isDisabled || this.uploading) &&
      (fileState.kind === 'none' || fileState.kind === 'cleared')
    );
  }

  override render() {
    const fileState = this.fileState;
    const canPick = this.canPick(fileState);
    // A drag over the element takes precedence over a (stale) error, which returns if it leaves
    const classes = {
      field: true,
      error: Boolean(this.errorMessage) && !this.dragging,
      dragging: this.dragging,
    };
    // The status is always present, so its changes are announced; the progress isn't within it,
    // to not be announced too
    return html`
      <div class=${classMap(classes)} part="field">
        ${canPick && !this.dragging ? this.renderChoose() : this.renderLeadIcon()}
        <div class="text">
          <div class="primary">${this.renderPrimary(fileState)}</div>
          <div class="status" role="status" tabindex="-1">${this.renderStatus(fileState)}</div>
        </div>
        ${this.renderTrailing(fileState)}
        ${this.uploading ? html`<progress part="progress" aria-label="Upload progress" value=${this.uploadFraction ?? nothing}></progress>` : null}
      </div>
    `;
  }

  private renderChoose(): TemplateResult {
    return html`<label class="choose" part="button">
      <input id="picker" class="picker" type="file" @change=${this.handlePickerChange} />
      ${uploadIcon}Choose file
    </label>`;
  }

  private renderLeadIcon(): TemplateResult {
    return html`<span class="lead">${this.dragging ? uploadIcon : fileIcon}</span>`;
  }

  private renderPrimary(fileState: FileState): string | TemplateResult | null {
    if (this.dragging) {
      return 'Drop to upload';
    }
    if (this.errorMessage) {
      // The message is the status, alone
      return null;
    }
    if (this.uploadingFile) {
      return this.uploadingFile.name;
    }
    switch (fileState.kind) {
      // The name may be truncated, so it's also the tooltip, in full
      case 'pending': {
        const name = fileState.name || '(unknown file)';
        return html`<span title=${name}>${name}</span>`;
      }
      case 'kept':
        // The URL is unknown after a server-rendered clear is undone, so there's no name to show
        return fileState.url
          ? html`<a href=${fileState.url} title=${fileState.name}>${fileState.name}</a>`
          : null;
      case 'cleared':
        return null;
      default:
        return this.isDisabled ? 'No file' : html`<span class="muted">or drop it here</span>`;
    }
  }

  private renderStatus(fileState: FileState): string | null {
    if (this.dragging) {
      return this.renderLimit();
    }
    if (this.errorMessage) {
      return this.errorMessage;
    }
    if (this.uploading) {
      const progress = this.uploadProgress;
      return progress?.uploaded !== undefined && progress.total !== undefined
        ? `Uploading… ${formatBytes(progress.uploaded)} of ${formatBytes(progress.total)}`
        : 'Uploading…';
    }
    switch (fileState.kind) {
      case 'pending':
        return 'Uploaded, not yet saved';
      case 'cleared':
        return 'To be removed';
      case 'kept':
        return 'Current file';
      default:
        // The limit only matters when a file can be chosen
        return this.isDisabled ? null : this.renderLimit();
    }
  }

  private renderLimit(): string | null {
    const maxSize = this.maxSize;
    return maxSize !== undefined && maxSize > 0 && Number.isFinite(maxSize)
      ? `Up to ${formatBytes(maxSize)}`
      : null;
  }

  private renderTrailing(fileState: FileState): TemplateResult | null {
    if (this.isDisabled) {
      return null;
    }
    if (this.uploading) {
      const fraction = this.uploadFraction;
      return fraction === undefined
        ? null
        : html`<span class="percent">${Math.round(fraction * 100)}%</span>`;
    }
    switch (fileState.kind) {
      case 'pending':
      case 'kept':
        return html`<button type="button" class="remove" part="remove" aria-label="Remove" title="Remove" @click=${this.handleRemove}>${removeIcon}</button>`;
      case 'cleared':
        return html`<button type="button" class="undo" part="undo" @click=${this.handleUndo}>Undo</button>`;
      default:
        return null;
    }
  }

  private get uploadFraction(): number | undefined {
    const progress = this.uploadProgress;
    return progress?.uploaded !== undefined && progress.total
      ? progress.uploaded / progress.total
      : undefined;
  }

  private async handlePickerChange(): Promise<void> {
    const file = this.picker?.files?.[0];
    if (file !== undefined) {
      await this.acceptFile(file);
    }
  }

  private readonly handleHostClick = (event: MouseEvent): void => {
    // A click on the element's label (which the browser forwards to a labelable element) is
    // dispatched at the host itself, whereas a click within the element is dispatched at a shadow
    // descendant, and only retargeted to the host
    if (event.composedPath()[0] !== this) {
      return;
    }
    // Act as a native input would: open the picker, or else focus the control
    if (this.picker) {
      this.picker.click();
    } else {
      this.firstControl?.focus();
    }
  };

  private readonly handleDragOver = (event: DragEvent): void => {
    if (!(this.canPick(this.fileState) && event.dataTransfer?.types.includes('Files'))) {
      return;
    }
    // Claim the drop; the browser would otherwise open the file
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
    this.dragging = true;
  };

  private readonly handleDragLeave = (): void => {
    this.dragging = false;
  };

  private readonly handleDrop = async (event: DragEvent): Promise<void> => {
    this.dragging = false;
    if (!this.canPick(this.fileState)) {
      return;
    }
    event.preventDefault();
    // Only one file is represented, so any others are ignored
    const file = event.dataTransfer?.files[0];
    if (file !== undefined) {
      await this.acceptFile(file);
    }
  };

  private async acceptFile(file: File): Promise<void> {
    // The server refuses these too, but rejecting here avoids a needless attempt, and gives a
    // specific message
    if (file.size === 0) {
      this.resetPicker();
      this.errorMessage = 'File is empty.';
      return;
    }
    // A garbage (NaN) or negative limit is ignored, leaving it to the server
    const maxSize = this.maxSize ?? Number.POSITIVE_INFINITY;
    if (maxSize >= 0 && file.size > maxSize) {
      this.resetPicker();
      this.errorMessage = `File is too large (${formatBytes(file.size)}), maximum is ${formatBytes(maxSize)}.`;
      return;
    }

    await this.upload(file);
  }

  private handleRemove(): void {
    this.errorMessage = '';
    if (this.fileState.kind === 'pending') {
      // Discard the pending upload, reverting to the existing file, if any. On a redisplay, the
      // server renders only the pending file's info, so an existing file then goes unmentioned,
      // although it is kept.
      // TODO: Render the existing file's info alongside a pending value; currently,
      // "S3FormFileField.bound_data" returns only the pending data.
      this.value = '';
      this.uploadedFileName = '';
    } else {
      // Clear the kept file
      this.value = CLEAR_VALUE;
    }
    this.dispatchInput();
  }

  private handleUndo(): void {
    this.value = '';
    this.dispatchInput();
  }

  private readonly handleFormSubmit = (event: SubmitEvent): void => {
    // The element's validity blocks submission of most forms, but a "novalidate" form (as in
    // the Django admin) ignores validity, so block that here too
    if (this.uploading) {
      event.preventDefault();
      this.internals.reportValidity();
    }
  };

  private async upload(file: File): Promise<void> {
    this.uploadingFile = file;
    this.errorMessage = '';

    let fieldValue: string;
    try {
      fieldValue = await uploadFile(this.baseUrl, this.fieldId, file, (progress) => {
        this.uploadProgress = progress;
      });
    } catch {
      this.resetPicker();
      this.errorMessage = 'Error uploading file.';
      return;
    } finally {
      this.uploadingFile = undefined;
      this.uploadProgress = undefined;
    }

    this.value = fieldValue;
    this.uploadedFileName = file.name;
    this.dispatchInput();
  }

  /**
   * Discard any selected file, if the picker is present.
   *
   * This allows the same file to be reselected ("change" fires only on a change), and avoids
   * showing a rejected file as selected.
   */
  private resetPicker(): void {
    if (this.picker) {
      this.picker.value = '';
    }
  }
}

declare global {
  interface HTMLElementTagNameMap {
    's3-file-input': S3FileInputElement;
  }
}
