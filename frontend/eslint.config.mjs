import { react } from 'eslint-config-ali';

export default [
  ...react,
  {
    ignores: ['dist', 'node_modules', '*.tsbuildinfo'],
  },
];
