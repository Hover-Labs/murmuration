module.exports = {
  root: true,
  rules: {
    'prefer-template': 2
  },

  parser: '@typescript-eslint/parser', // Make ESLint compatible with TypeScript
  parserOptions: {
    // Enable linting rules with type information from our tsconfig
    tsconfigRootDir: __dirname,
    project: ['./tsconfig.eslint.json'],

    sourceType: 'module', // Allow the use of imports / ES modules

    ecmaFeatures: {
      impliedStrict: true, // Enable global strict mode
    },
  },

  // Specify global variables that are predefined
  env: {
    browser: true, // Enable browser global variables
    node: true, // Enable node global variables & Node.js scoping
    es2020: true, // Add all ECMAScript 2020 globals and automatically set the ecmaVersion parser option to ES2020
    jest: true, // Add Jest testing global variables
  },

  plugins: [
    '@typescript-eslint', // Add some TypeScript specific rules, and disable rules covered by the typechecker
    'import', // Add rules that help validate proper imports
    'jest', // Add rules for writing better Jest tests
    'prettier', // Allows running prettier as an ESLint rule, and reporting differences as individual linting issues
  ],

  extends: [
    // ESLint recommended rules
    'eslint:recommended',

    // Add TypeScript-specific rules, and disable rules covered by typechecker
    'plugin:@typescript-eslint/eslint-recommended',
    'plugin:@typescript-eslint/recommended',

    // Add rules for import/export syntax
    'plugin:import/errors',
    'plugin:import/warnings',
    'plugin:import/typescript',

    // Add rules for Jest-specific syntax
    'plugin:jest/recommended',

    // Add rules that specifically require type information using our tsconfig
    'plugin:@typescript-eslint/recommended-requiring-type-checking',

    // Enable Prettier for ESLint --fix, and disable rules that conflict with Prettier
    'prettier/@typescript-eslint',
    'plugin:prettier/recommended',
  ],

  // rules: {
  //   // This rule is about explicitly using `return undefined` when a function returns any non-undefined object.
  //   // However, since we're using TypeScript, it will yell at us if a function is not allowed to return `undefined` in its signature, so we don't need this rule.
  //   "consistent-return": "off",
  // },

  overrides: [
    // Overrides for all test files
    {
      files: '__tests__/**/*.ts',
      rules: {
        // For our just test files, the pattern has been to have unnamed functions
        'func-names': 'off',
        // Using non-null assertions (obj!.property) cancels the benefits of the strict null-checking mode, but these are test files, so we don't care.
        '@typescript-eslint/no-non-null-assertion': 'off',
        // For some test files, we shadow testing constants with function parameter names
        'no-shadow': 'off',
        // Some of our test files declare helper classes with errors
        'max-classes-per-file': 'off',
      },
    },
    {
      files: '**/*.ts',
      rules: {
        // Allow unused variables in our files when explicitly prepended with `_`.
        '@typescript-eslint/no-unused-vars': [
          'error',
          { argsIgnorePattern: '^_' },
        ],

        // Allow us to import computed values for GRPC package definitions
        'import/namespace': [2, { allowComputed: true }],

        // These rules are deprecated, but we have an old config that enables it
        '@typescript-eslint/camelcase': 'off',
        '@typescript-eslint/ban-ts-ignore': 'off',
      },
    },
  ],
}