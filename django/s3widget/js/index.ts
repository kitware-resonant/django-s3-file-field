import { DEFAULT_BASE_URL } from "./constants";

export function init(elem: HTMLInputElement) {
  console.log(elem);
  const baseUrl = elem.dataset.s3fileinput || DEFAULT_BASE_URL;
}

(function (factory) {
  // in case the document is already rendered
  if (document.readyState != 'loading') {
    factory();
  } else {
    document.addEventListener('DOMContentLoaded', factory);
  }
})(function () {
  // auto init
  const inputs = Array.from(document.querySelectorAll<HTMLInputElement>('input[type=file][data-s3fileinput]'));
  inputs.forEach(init);
});
