import S3FileInput from "./S3FileInput";

(function (factory) {
  // in case the document is already rendered
  if (document.readyState != 'loading') {
    factory();
  } else {
    document.addEventListener('DOMContentLoaded', factory);
  }
})(function () {
  // auto init
  const wrappers = Array.from(document.querySelectorAll<HTMLInputElement>('input[data-s3fileinput]'));
  wrappers.forEach((w) => new S3FileInput(w));
});
