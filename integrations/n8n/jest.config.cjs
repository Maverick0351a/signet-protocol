/** @type {import('jest').Config} */
module.exports = {
  testMatch: ['**/test/**/*.test.ts'],
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', { tsconfig: 'tsconfig.json' }],
  },
  testEnvironment: 'node',
  verbose: true,
  moduleFileExtensions: ['ts', 'js', 'json'],
  roots: ['<rootDir>'],
  collectCoverage: false,
};
