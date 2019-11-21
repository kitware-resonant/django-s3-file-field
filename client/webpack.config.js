const path = require('path');

function gen(declarations = false) {
  return {
    resolve: {
      // Add `.ts` and `.tsx` as a resolvable extension.
      extensions: [".ts", ".tsx", ".js"]
    },
    module: {
      rules: [
        // all files with a `.ts` or `.tsx` extension will be handled by `ts-loader`
        {
          test: /\.tsx?$/,
          loader: "ts-loader",
          options: declarations
            ? {
                compilerOptions: {
                  declaration: true,
                  declarationDir: "build"
                }
              }
            : {}
        },
        {
          test: /\.s[ac]ss$/i,
          use: [
            // Creates `style` nodes from JS strings
            "style-loader",
            // Translates CSS into CommonJS
            "css-loader",
            // Compiles Sass to CSS
            "sass-loader"
          ]
        }
      ]
    }
  };
}

module.exports = [
  {
    entry: "./src/index.ts",
    output: {
      path: path.resolve("build"),
      filename: "joist.js",
      libraryExport: "Joist",
      libraryTarget: "umd"
    },
    ...gen(true)
  },
  {
    entry: "./src/widget.ts",
    output: {
      path: path.resolve("../joist/static/joist/"),
      filename: "joist.js",
      libraryExport: "Joist",
      libraryTarget: "umd"
    },
    ...gen()
  }
];
