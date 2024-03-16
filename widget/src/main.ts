import App from './App.svelte';

const targetInput = document.querySelector('input[data-s3fileinput]') as Element;
const parent = targetInput.parentNode;
const wrapper = document.createElement('div');
parent?.replaceChild(wrapper, targetInput);
wrapper.appendChild(targetInput);

const app = new App({
  target: document.querySelector('input[data-s3fileinput]')?.parentNode as Element,
  props: {
    name: 'world',
  },
});

export default app;
