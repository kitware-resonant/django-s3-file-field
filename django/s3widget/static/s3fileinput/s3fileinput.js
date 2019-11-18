(function (factory) {
  // in case the document is already rendered
  if (document.readyState != 'loading') {
    factory();
  } else {
    document.addEventListener('DOMContentLoaded', factory);
  }
})(function () {
  const inputs = Array.from(document.querySelectorAll('input[type=file][data-s3fileinput]'));
  console.log(inputs);
});
