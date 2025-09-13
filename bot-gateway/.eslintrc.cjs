/* eslint-env node */
module.exports = {
  root: true,
  env: { es2023: true, node: true },
  extends: ['standard'],
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  rules: {
    'no-console': 'off',
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }]
  },
  ignorePatterns: ['node_modules/', 'dist/']
};
