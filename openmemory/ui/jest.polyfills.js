// jest.polyfills.js
/**
 * @note The block below contains polyfills for Node.js globals
 * required for Jest to function when running JSDOM tests.
 * These HAVE to be require's and HAVE to be in this exact
 * order, since "undici" depends on the "TextEncoder" global API.
 */

const { TextDecoder, TextEncoder } = require('node:util')

Object.defineProperties(globalThis, {
  TextDecoder: { value: TextDecoder },
  TextEncoder: { value: TextEncoder },
})

// Polyfill for fetch API
require('whatwg-fetch')

// Polyfill for crypto API
const { webcrypto } = require('node:crypto')

Object.defineProperties(globalThis, {
  crypto: {
    value: webcrypto,
    configurable: true,
    writable: true,
  },
})

// Polyfill for URL API
const { URL, URLSearchParams } = require('node:url')

Object.defineProperties(globalThis, {
  URL: { value: URL },
  URLSearchParams: { value: URLSearchParams },
})

// Add other polyfills as needed
