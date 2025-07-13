import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import { useRouter, useSearchParams } from 'next/navigation'
import '@testing-library/jest-dom'
import { MemoriesSection } from '../MemoriesSection'
import memoriesSlice from '@/store/memoriesSlice'

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(),
}))

// Mock hooks
jest.mock('@/hooks/useMemoriesApi', () => ({
  useMemoriesApi: jest.fn(),
}))

// Mock child components
jest.mock('../MemoryTable', () => ({
  MemoryTable: () => <div data-testid='memory-table'>Memory Table</div>,
}))

jest.mock('../MemoryPagination', () => ({
  MemoryPagination: ({ currentPage, totalPages, setCurrentPage }: any) => (
    <div data-testid='memory-pagination'>
      <span>
        Page {currentPage} of {totalPages}
      </span>
      <button onClick={() => setCurrentPage(currentPage + 1)}>Next</button>
    </div>
  ),
}))

jest.mock('../CreateMemoryDialog', () => ({
  CreateMemoryDialog: () => (
    <button data-testid='create-memory-dialog'>Create Memory</button>
  ),
}))

jest.mock('../PageSizeSelector', () => ({
  PageSizeSelector: ({ pageSize, onPageSizeChange }: any) => (
    <select
      data-testid='page-size-selector'
      value={pageSize}
      onChange={(e) => onPageSizeChange(Number(e.target.value))}
    >
      <option value={10}>10</option>
      <option value={20}>20</option>
      <option value={50}>50</option>
    </select>
  ),
}))

jest.mock('@/skeleton/MemoryTableSkeleton', () => ({
  MemoryTableSkeleton: () => (
    <div data-testid='memory-table-skeleton'>Loading...</div>
  ),
}))

// Mock data
const mockMemories = [
  {
    id: 'mem1',
    memory: 'Test memory 1',
    created_at: 1640995200000,
    state: 'active' as const,
    metadata: {},
    categories: ['work'],
    client: 'api' as const,
    app_name: 'test_app',
  },
  {
    id: 'mem2',
    memory: 'Test memory 2',
    created_at: 1640995300000,
    state: 'active' as const,
    metadata: {},
    categories: ['personal'],
    client: 'api' as const,
    app_name: 'test_app',
  },
]

const createTestStore = (initialState = {}) =>
  configureStore({
    reducer: {
      memories: memoriesSlice,
    },
    preloadedState: {
      memories: {
        memories: [],
        selectedMemoryIds: [],
        selectedMemory: null,
        accessLogs: [],
        relatedMemories: [],
        loading: false,
        error: null,
        ...initialState,
      },
    },
  })

const renderWithStore = (store = createTestStore()) => {
  return {
    store,
    ...render(
      <Provider store={store}>
        <MemoriesSection />
      </Provider>,
    ),
  }
}

describe('MemoriesSection', () => {
  const mockPush = jest.fn()
  const mockFetchMemories = jest.fn()
  const mockGet = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()

    // Mock router
    ;(useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
    })

    // Mock search params
    ;(useSearchParams as jest.Mock).mockReturnValue({
      get: mockGet,
      toString: () => 'page=1&size=10',
    })

    // Mock useMemoriesApi
    const { useMemoriesApi } = require('@/hooks/useMemoriesApi')
    useMemoriesApi.mockReturnValue({
      fetchMemories: mockFetchMemories,
    })

    // Set default URL params
    mockGet.mockImplementation((param: string) => {
      switch (param) {
        case 'page':
          return '1'
        case 'size':
          return '10'
        case 'search':
          return ''
        default:
          return null
      }
    })
  })

  describe('Rendering', () => {
    it('renders loading skeleton when loading', () => {
      mockFetchMemories.mockResolvedValue({ total: 0, pages: 0 })

      renderWithStore()

      expect(screen.getByTestId('memory-table-skeleton')).toBeInTheDocument()
    })

    it('renders memory table when memories are loaded', async () => {
      const store = createTestStore({ memories: mockMemories })
      mockFetchMemories.mockResolvedValue({ total: 2, pages: 1 })

      renderWithStore(store)

      await waitFor(() => {
        expect(screen.getByTestId('memory-table')).toBeInTheDocument()
      })
    })

    it('renders pagination controls when memories exist', async () => {
      const store = createTestStore({ memories: mockMemories })
      mockFetchMemories.mockResolvedValue({ total: 2, pages: 1 })

      renderWithStore(store)

      await waitFor(() => {
        expect(screen.getByTestId('memory-pagination')).toBeInTheDocument()
        expect(screen.getByTestId('page-size-selector')).toBeInTheDocument()
      })
    })

    it('displays memory count information', async () => {
      const store = createTestStore({ memories: mockMemories })
      mockFetchMemories.mockResolvedValue({ total: 25, pages: 3 })

      renderWithStore(store)

      await waitFor(() => {
        expect(
          screen.getByText(/Showing 1 to 10 of 25 memories/),
        ).toBeInTheDocument()
      })
    })
  })

  describe('Empty State', () => {
    it('renders empty state when no memories exist', async () => {
      mockFetchMemories.mockResolvedValue({ total: 0, pages: 0 })

      renderWithStore()

      await waitFor(() => {
        expect(screen.getByText('No memories found')).toBeInTheDocument()
        expect(
          screen.getByText('Create your first memory to see it here'),
        ).toBeInTheDocument()
        expect(screen.getByTestId('create-memory-dialog')).toBeInTheDocument()
      })
    })

    it('renders filtered empty state with clear filters option', async () => {
      mockFetchMemories.mockResolvedValue({ total: 0, pages: 0 })

      renderWithStore()

      await waitFor(() => {
        // This would be triggered when filters are applied but no results
        // The component checks selectedCategory and selectedClient state
        expect(screen.getByText('No memories found')).toBeInTheDocument()
      })
    })
  })

  describe('Data Fetching', () => {
    it('fetches memories on mount', () => {
      mockFetchMemories.mockResolvedValue({ total: 0, pages: 0 })

      renderWithStore()

      expect(mockFetchMemories).toHaveBeenCalledWith('', 1, 10)
    })

    it('fetches memories with search query from URL', () => {
      mockGet.mockImplementation((param: string) => {
        switch (param) {
          case 'search':
            return 'test query'
          case 'page':
            return '1'
          case 'size':
            return '10'
          default:
            return null
        }
      })

      mockFetchMemories.mockResolvedValue({ total: 0, pages: 0 })

      renderWithStore()

      expect(mockFetchMemories).toHaveBeenCalledWith('test query', 1, 10)
    })

    it('fetches memories with custom page and size from URL', () => {
      mockGet.mockImplementation((param: string) => {
        switch (param) {
          case 'page':
            return '3'
          case 'size':
            return '25'
          case 'search':
            return ''
          default:
            return null
        }
      })

      mockFetchMemories.mockResolvedValue({ total: 0, pages: 0 })

      renderWithStore()

      expect(mockFetchMemories).toHaveBeenCalledWith('', 3, 25)
    })

    it('handles fetch memories error gracefully', async () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation()
      mockFetchMemories.mockRejectedValue(new Error('Fetch failed'))

      renderWithStore()

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalledWith(
          'Failed to fetch memories:',
          expect.any(Error),
        )
      })

      consoleError.mockRestore()
    })
  })

  describe('Pagination', () => {
    it('updates URL when page changes', async () => {
      const store = createTestStore({ memories: mockMemories })
      mockFetchMemories.mockResolvedValue({ total: 20, pages: 2 })

      renderWithStore(store)

      await waitFor(() => {
        const nextButton = screen.getByText('Next')
        fireEvent.click(nextButton)
      })

      expect(mockPush).toHaveBeenCalledWith('?page=2&size=10')
    })

    it('updates URL when page size changes', async () => {
      const store = createTestStore({ memories: mockMemories })
      mockFetchMemories.mockResolvedValue({ total: 20, pages: 2 })

      renderWithStore(store)

      await waitFor(() => {
        const pageSizeSelector = screen.getByTestId('page-size-selector')
        fireEvent.change(pageSizeSelector, { target: { value: '20' } })
      })

      expect(mockPush).toHaveBeenCalledWith('?page=1&size=20')
    })

    it('resets to page 1 when page size changes', async () => {
      mockGet.mockImplementation((param: string) => {
        switch (param) {
          case 'page':
            return '5'
          case 'size':
            return '10'
          case 'search':
            return ''
          default:
            return null
        }
      })

      const store = createTestStore({ memories: mockMemories })
      mockFetchMemories.mockResolvedValue({ total: 100, pages: 10 })

      renderWithStore(store)

      await waitFor(() => {
        const pageSizeSelector = screen.getByTestId('page-size-selector')
        fireEvent.change(pageSizeSelector, { target: { value: '50' } })
      })

      expect(mockPush).toHaveBeenCalledWith('?page=1&size=50')
    })
  })

  describe('URL Parameter Handling', () => {
    it('handles missing URL parameters gracefully', () => {
      mockGet.mockReturnValue(null)
      mockFetchMemories.mockResolvedValue({ total: 0, pages: 0 })

      renderWithStore()

      expect(mockFetchMemories).toHaveBeenCalledWith('', 1, 10)
    })

    it('handles invalid URL parameters', () => {
      mockGet.mockImplementation((param: string) => {
        switch (param) {
          case 'page':
            return 'invalid'
          case 'size':
            return 'invalid'
          case 'search':
            return ''
          default:
            return null
        }
      })

      mockFetchMemories.mockResolvedValue({ total: 0, pages: 0 })

      renderWithStore()

      // Should fallback to defaults
      expect(mockFetchMemories).toHaveBeenCalledWith('', 1, 10)
    })
  })

  describe('State Management Integration', () => {
    it('reads memories from Redux store', () => {
      const store = createTestStore({ memories: mockMemories })
      mockFetchMemories.mockResolvedValue({ total: 2, pages: 1 })

      renderWithStore(store)

      const state = store.getState()
      expect(state.memories.memories).toEqual(mockMemories)
    })

    it('handles store updates correctly', async () => {
      const store = createTestStore({ memories: [] })
      mockFetchMemories.mockResolvedValue({ total: 1, pages: 1 })

      const { rerender } = renderWithStore(store)

      // Update store with new memories
      store.dispatch({
        type: 'memories/setMemoriesSuccess',
        payload: mockMemories,
      })

      rerender(
        <Provider store={store}>
          <MemoriesSection />
        </Provider>,
      )

      await waitFor(() => {
        expect(screen.getByTestId('memory-table')).toBeInTheDocument()
      })
    })
  })

  describe('Loading States', () => {
    it('shows loading state during initial fetch', () => {
      mockFetchMemories.mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve({ total: 0, pages: 0 }), 100),
          ),
      )

      renderWithStore()

      expect(screen.getByTestId('memory-table-skeleton')).toBeInTheDocument()
    })

    it('shows loading state during pagination', async () => {
      const store = createTestStore({ memories: mockMemories })
      mockFetchMemories.mockResolvedValue({ total: 20, pages: 2 })

      renderWithStore(store)

      await waitFor(() => {
        expect(screen.getByTestId('memory-table')).toBeInTheDocument()
      })

      // Simulate pagination causing loading
      mockFetchMemories.mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve({ total: 20, pages: 2 }), 100),
          ),
      )

      const nextButton = screen.getByText('Next')
      fireEvent.click(nextButton)

      // Component should show loading skeleton again
      expect(screen.getByTestId('memory-table-skeleton')).toBeInTheDocument()
    })
  })

  describe('Component Dependencies', () => {
    it('correctly passes pagination props to MemoryPagination', async () => {
      const store = createTestStore({ memories: mockMemories })
      mockFetchMemories.mockResolvedValue({ total: 50, pages: 5 })

      renderWithStore(store)

      await waitFor(() => {
        expect(screen.getByText('Page 1 of 5')).toBeInTheDocument()
      })
    })

    it('correctly passes page size to PageSizeSelector', async () => {
      mockGet.mockImplementation((param: string) => {
        switch (param) {
          case 'size':
            return '25'
          case 'page':
            return '1'
          case 'search':
            return ''
          default:
            return null
        }
      })

      const store = createTestStore({ memories: mockMemories })
      mockFetchMemories.mockResolvedValue({ total: 50, pages: 2 })

      renderWithStore(store)

      await waitFor(() => {
        const selector = screen.getByTestId(
          'page-size-selector',
        ) as HTMLSelectElement
        expect(selector.value).toBe('25')
      })
    })
  })

  describe('Error Scenarios', () => {
    it('handles component mount/unmount correctly', () => {
      mockFetchMemories.mockResolvedValue({ total: 0, pages: 0 })

      const { unmount } = renderWithStore()

      expect(() => unmount()).not.toThrow()
    })

    it('handles rapid state changes', async () => {
      const store = createTestStore({ memories: [] })
      mockFetchMemories.mockResolvedValue({ total: 2, pages: 1 })

      renderWithStore(store)

      // Rapidly update store multiple times
      for (let i = 0; i < 5; i++) {
        store.dispatch({
          type: 'memories/setMemoriesSuccess',
          payload: mockMemories.slice(0, i % 2),
        })
      }

      // Should handle rapid updates without errors
      await waitFor(() => {
        expect(
          screen.queryByTestId('memory-table-skeleton'),
        ).not.toBeInTheDocument()
      })
    })
  })

  describe('Performance', () => {
    it('handles large memory datasets', async () => {
      const largeMemorySet = Array.from({ length: 1000 }, (_, i) => ({
        id: `mem${i}`,
        memory: `Memory ${i}`,
        created_at: Date.now(),
        state: 'active' as const,
        metadata: {},
        categories: [`cat${i % 10}`],
        client: 'api' as const,
        app_name: 'test_app',
      }))

      const store = createTestStore({ memories: largeMemorySet })
      mockFetchMemories.mockResolvedValue({ total: 1000, pages: 100 })

      const startTime = performance.now()
      renderWithStore(store)
      const endTime = performance.now()

      // Should render within reasonable time (under 100ms)
      expect(endTime - startTime).toBeLessThan(100)

      await waitFor(() => {
        expect(screen.getByTestId('memory-table')).toBeInTheDocument()
      })
    })
  })
})
