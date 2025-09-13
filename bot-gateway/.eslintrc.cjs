/* eslint-env node */
export default {
  root: true,
  env: { es2023: true, node: true },
  extends: ['standard'],
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  rules: {
    // projektfreundliche Defaults
    'no-console': 'off',
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }]
  },
  ignorePatterns: ['node_modules/', 'dist/']
}
