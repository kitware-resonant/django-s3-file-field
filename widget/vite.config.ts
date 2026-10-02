import babel, { type RolldownBabelPreset } from '@rolldown/plugin-babel';
import { defineConfig } from 'vite';

// Vite's Oxc transformer cannot lower standard (TC39) decorators, as used by Lit, so Babel is
// used for that alone, per https://vite.dev/guide/migration#decorators
function decoratorPreset(options: Record<string, unknown>): RolldownBabelPreset {
  return {
    preset: () => ({
      plugins: [['@babel/plugin-proposal-decorators', options]],
    }),
    rolldown: {
      // Only run this transform if the file contains a decorator
      filter: {
        code: '@',
      },
    },
  };
}

export default defineConfig({
  input: ['./src/s3-file-input.ts', './src/s3-file-input.css'],
  plugins: [babel({ presets: [decoratorPreset({ version: '2023-11' })] })],
  build: {
    lib: {
      // The S3FileInput widget loads this with a 'type="module"' script tag
      formats: ['es'],
      // The output files are named after the inputs
    },
    // Emit the stylesheet input as its own file, which library mode otherwise disallows
    cssCodeSplit: true,
    outDir: '../s3_file_field/static/s3_file_field',
    // The outDir is outside the project root, so Vite won't empty it by default
    emptyOutDir: true,
  },
});
