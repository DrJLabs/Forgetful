// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'

// Mock Next.js router
import { jest } from '@jest/globals'

jest.mock('next/router', () => ({
  useRouter() {
    return {
      route: '/',
      pathname: '/',
      query: {},
      asPath: '/',
      push: jest.fn(),
      pop: jest.fn(),
      reload: jest.fn(),
      back: jest.fn(),
      prefetch: jest.fn().mockResolvedValue(undefined),
      beforePopState: jest.fn(),
      events: {
        on: jest.fn(),
        off: jest.fn(),
        emit: jest.fn(),
      },
      isFallback: false,
      isLocaleDomain: false,
      isReady: true,
      isPreview: false,
    }
  },
}))

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      refresh: jest.fn(),
    }
  },
  useSearchParams() {
    return new URLSearchParams()
  },
  usePathname() {
    return '/'
  },
}))

// Mock Next.js Image component
jest.mock('next/image', () => ({
  __esModule: true,
  default: (props) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img {...props} />
  },
}))

// Mock Next.js Link component
jest.mock('next/link', () => ({
  __esModule: true,
  default: ({ children, href, ...rest }) => {
    return (
      <a href={href} {...rest}>
        {children}
      </a>
    )
  },
}))

// Mock Next.js Head component
jest.mock('next/head', () => {
  return {
    __esModule: true,
    default: ({ children }) => {
      return children
    },
  }
})

// Mock environment variables
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'
process.env.NODE_ENV = 'test'

// Mock fetch globally
global.fetch = jest.fn()

// Mock console methods to reduce noise in tests
const originalError = console.error
const originalWarn = console.warn

beforeAll(() => {
  console.error = (...args) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOMTestUtils.act is deprecated')
    ) {
      return
    }
    originalError.call(console, ...args)
  }

  console.warn = (...args) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('componentWillReceiveProps') ||
        args[0].includes('componentWillUpdate'))
    ) {
      return
    }
    originalWarn.call(console, ...args)
  }
})

afterAll(() => {
  console.error = originalError
  console.warn = originalWarn
})

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})

// Mock window.IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}

  disconnect() {
    return null
  }

  observe() {
    return null
  }

  unobserve() {
    return null
  }
}

// Mock window.ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}

  disconnect() {
    return null
  }

  observe() {
    return null
  }

  unobserve() {
    return null
  }
}

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
global.localStorage = localStorageMock

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
global.sessionStorage = sessionStorageMock

// Setup global test utilities
global.testUtils = {
  // Mock API responses
  mockApiResponse: (data, status = 200) => {
    return Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      statusText: status === 200 ? 'OK' : 'Error',
      json: () => Promise.resolve(data),
      text: () => Promise.resolve(JSON.stringify(data)),
    })
  },

  // Mock API error
  mockApiError: (message = 'API Error', status = 500) => {
    return Promise.reject({
      ok: false,
      status,
      statusText: 'Error',
      message,
    })
  },

  // Create mock memory data
  createMockMemory: (overrides = {}) => ({
    id: 'test-memory-id',
    content: 'Test memory content',
    user_id: 'test-user',
    app_id: 'test-app',
    metadata: { category: 'test' },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }),

  // Create mock user data
  createMockUser: (overrides = {}) => ({
    id: 'test-user-uuid',
    user_id: 'test-user',
    name: 'Test User',
    email: 'test@example.com',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }),

  // Create mock app data
  createMockApp: (overrides = {}) => ({
    id: 'test-app-uuid',
    app_id: 'test-app',
    name: 'Test App',
    description: 'Test application',
    user_id: 'test-user',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }),

  // Wait for async updates
  waitForAsync: () => new Promise(resolve => setTimeout(resolve, 0)),
}

// Custom jest matchers
expect.extend({
  toBeVisible(received) {
    const pass = received && received.style.display !== 'none'
    if (pass) {
      return {
        message: () => `expected element not to be visible`,
        pass: true,
      }
    } else {
      return {
        message: () => `expected element to be visible`,
        pass: false,
      }
    }
  },

  toHaveLoadingState(received) {
    const hasLoadingClass = received.classList.contains('loading')
    const hasLoadingAttribute = received.hasAttribute('data-loading')
    const pass = hasLoadingClass || hasLoadingAttribute

    if (pass) {
      return {
        message: () => `expected element not to have loading state`,
        pass: true,
      }
    } else {
      return {
        message: () => `expected element to have loading state`,
        pass: false,
      }
    }
  },
})

// Setup and teardown for each test
beforeEach(() => {
  // Clear all mocks before each test
  jest.clearAllMocks()
  
  // Reset fetch mock
  if (global.fetch && global.fetch.mockClear) {
    global.fetch.mockClear()
  }

  // Clear localStorage and sessionStorage
  localStorage.clear()
  sessionStorage.clear()
})

afterEach(() => {
  // Additional cleanup after each test
  jest.restoreAllMocks()
})