import type { Config } from 'jest'
import nextJest from 'next/jest.js'

const createJestConfig = nextJest({ dir: './' })

const config: Config = {
  coverageProvider: 'v8',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  // Explicit path alias mapping — jest.mock() uses the resolver, not the SWC
  // transform, so @/* aliases must be in moduleNameMapper to work with mocks.
  // Also force CJS builds for @tanstack packages that expose @tanstack/custom-condition
  // pointing to raw TypeScript source.
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@tanstack/react-query$':
      '<rootDir>/node_modules/@tanstack/react-query/build/legacy/index.cjs',
    '^@tanstack/query-core$':
      '<rootDir>/node_modules/@tanstack/query-core/build/legacy/index.cjs',
  },
}

export default createJestConfig(config)
