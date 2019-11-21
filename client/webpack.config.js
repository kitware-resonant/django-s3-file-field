const path = require('path');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

function gen(bundle = false) {
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
          options: bundle
            ? {
              configFile: "./tsconfig.lib.json"
            } : {}
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
    },

  };
}

module.exports = [
  {
    entry: "./src/bundle.ts",
    output: {
      path: path.resolve("build"),
      filename: "joist.js",
      libraryExport: "Joist",
      libraryTarget: "umd"
    },
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
          options: {
            configFile: "tsconfig.lib.json"
          }
        },
        {
          test: /\.s[ac]ss$/i,
          use: [
            {loader: MiniCssExtractPlugin.loader},
            "css-loader",
            "sass-loader"
          ]
        }
      ]
    },
    plugins: [
      new MiniCssExtractPlugin(),
    ],
  },
  {
    entry: "./src/widget.ts",
    output: {
      path: path.resolve("../joist/static/joist/"),
      filename: "joist.js",
      libraryExport: "Joist",
      libraryTarget: "umd"
    },
    resolve: {
      extensions: [".ts", ".tsx", ".js"]
    },
    module: {
      rules: [
        {
          test: /\.tsx?$/,
          loader: "ts-loader"
        },
        {
          test: /\.s[ac]ss$/i,
          use: ["style-loader", "css-loader", "sass-loader"]
        }
      ]
    }
  }
];
