// ESLint v9 flat config for the VS Code extension
// Mirrors the prior .eslintrc.json minimal rules using the TS parser
const tsParser = require("@typescript-eslint/parser");
const tsPlugin = require("@typescript-eslint/eslint-plugin");

/** @type {import('eslint').Linter.FlatConfig[]} */
module.exports = [
  {
    files: ["src/**/*.ts", "src/**/*.tsx"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parser: tsParser,
      parserOptions: {
        project: "./tsconfig.json",
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
    },
    rules: {
      "no-unused-vars": "off",
      "no-undef": "off",
    },
  },
];
