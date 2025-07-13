import { renderHook, act, waitFor } from '@testing-library/react'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import axios from 'axios'
import { useMemoriesApi } from '../useMemoriesApi'
import memoriesSlice from '@/store/memoriesSlice'
import profileSlice from '@/store/profileSlice'

// Mock axios
jest.mock('axios')
const mockedAxios = axios as jest.Mocked<typeof axios>

// Mock data
const mockMemoryData = {
  id: 'mem_123',
  content: 'Test memory content',
  created_at: '2024-01-01T00:00:00Z',
  state: 'active',
  metadata_: { category: 'test' },
  categories: ['work', 'project'],
  app_name: 'test_app'
}

const mockApiResponse = {
  items: [mockMemoryData],
  total: 1,
  pages: 1,
  page: 1,
  size: 10
}

const mockSimpleMemory = {
  id: 'mem_123',
  text: 'Test memory content',
  created_at: '2024-01-01T00:00:00Z',
  state: 'active',
  categories: ['work', 'project'],
  app_name: 'test_app'
}

// Create test store
const createTestStore = () => configureStore({
  reducer: {
    memories: memoriesSlice,
    profile: profileSlice
  },
  preloadedState: {
    memories: {
      memories: [],
      selectedMemoryIds: [],
      selectedMemory: null,
      accessLogs: [],
      relatedMemories: [],
      loading: false,
      error: null
    },
    profile: {
      userId: 'test_user',
      totalMemories: 0,
      totalApps: 0,
      apps: []
    }
  }
})

const renderHookWithStore = (store = createTestStore()) => {
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  )
  return { store, ...renderHook(() => useMemoriesApi(), { wrapper }) }
}

describe('useMemoriesApi', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8765'
  })

  describe('fetchMemories', () => {
    it('should fetch memories successfully', async () => {
      mockedAxios.post.mockResolvedValueOnce({ data: mockApiResponse })

      const { result } = renderHookWithStore()

      await act(async () => {
        const response = await result.current.fetchMemories()
        expect(response.total).toBe(1)
        expect(response.memories).toHaveLength(1)
        expect(response.memories[0].memory).toBe('Test memory content')
      })

      expect(mockedAxios.post).toHaveBeenCalledWith(
        'http://localhost:8765/api/v1/memories/filter',
        {
          user_id: 'test_user',
          page: 1,
          size: 10,
          search_query: undefined,
          app_ids: undefined,
          category_ids: undefined,
          sort_column: undefined,
          sort_direction: undefined,
          show_archived: undefined
        }
      )
    })

    it('should fetch memories with search query and filters', async () => {
      mockedAxios.post.mockResolvedValueOnce({ data: mockApiResponse })

      const { result } = renderHookWithStore()

      await act(async () => {
        await result.current.fetchMemories('test query', 2, 20, {
          apps: ['app1', 'app2'],
          categories: ['cat1'],
          sortColumn: 'created_at',
          sortDirection: 'desc',
          showArchived: true
        })
      })

      expect(mockedAxios.post).toHaveBeenCalledWith(
        'http://localhost:8765/api/v1/memories/filter',
        {
          user_id: 'test_user',
          page: 2,
          size: 20,
          search_query: 'test query',
          app_ids: ['app1', 'app2'],
          category_ids: ['cat1'],
          sort_column: 'created_at',
          sort_direction: 'desc',
          show_archived: true
        }
      )
    })

    it('should handle fetch memories error', async () => {
      const errorMessage = 'Network error'
      mockedAxios.post.mockRejectedValueOnce(new Error(errorMessage))

      const { result } = renderHookWithStore()

      await act(async () => {
        await expect(result.current.fetchMemories()).rejects.toThrow(errorMessage)
      })

      expect(result.current.error).toBe(errorMessage)
      expect(result.current.isLoading).toBe(false)
    })

    it('should set loading state correctly', async () => {
      // Mock a delayed response
      mockedAxios.post.mockImplementation(() =>
        new Promise(resolve => setTimeout(() => resolve({ data: mockApiResponse }), 100))
      )

      const { result } = renderHookWithStore()

      act(() => {
        result.current.fetchMemories()
      })

      expect(result.current.isLoading).toBe(true)

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })
    })
  })

  describe('createMemory', () => {
    it('should create memory successfully', async () => {
      mockedAxios.post.mockResolvedValueOnce({ data: mockMemoryData })

      const { result } = renderHookWithStore()

      await act(async () => {
        await result.current.createMemory('New memory content')
      })

      expect(mockedAxios.post).toHaveBeenCalledWith(
        'http://localhost:8765/api/v1/memories/',
        {
          user_id: 'test_user',
          text: 'New memory content',
          infer: false,
          app: 'openmemory'
        }
      )
    })

    it('should handle create memory error', async () => {
      const errorMessage = 'Failed to create memory'
      mockedAxios.post.mockRejectedValueOnce(new Error(errorMessage))

      const { result } = renderHookWithStore()

      await act(async () => {
        await expect(result.current.createMemory('New memory')).rejects.toThrow(errorMessage)
      })

      expect(result.current.error).toBe(errorMessage)
    })
  })

  describe('deleteMemories', () => {
    it('should delete memories successfully', async () => {
      mockedAxios.delete.mockResolvedValueOnce({ data: {} })

      const store = createTestStore()
      // Add some memories to the store first
      store.dispatch({
        type: 'memories/setMemoriesSuccess',
        payload: [
          { id: 'mem1', memory: 'Memory 1' },
          { id: 'mem2', memory: 'Memory 2' },
          { id: 'mem3', memory: 'Memory 3' }
        ]
      })

      const { result } = renderHookWithStore(store)

      await act(async () => {
        await result.current.deleteMemories(['mem1', 'mem2'])
      })

      expect(mockedAxios.delete).toHaveBeenCalledWith(
        'http://localhost:8765/api/v1/memories/',
        {
          data: {
            memory_ids: ['mem1', 'mem2'],
            user_id: 'test_user'
          }
        }
      )

      // Check that memories were removed from store
      const state = store.getState()
      expect(state.memories.memories).toHaveLength(1)
      expect(state.memories.memories[0].id).toBe('mem3')
    })

    it('should handle delete memories error', async () => {
      const errorMessage = 'Failed to delete memories'
      mockedAxios.delete.mockRejectedValueOnce(new Error(errorMessage))

      const { result } = renderHookWithStore()

      await act(async () => {
        await expect(result.current.deleteMemories(['mem1'])).rejects.toThrow(errorMessage)
      })

      expect(result.current.error).toBe(errorMessage)
    })
  })

  describe('fetchMemoryById', () => {
    it('should fetch memory by ID successfully', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockSimpleMemory })

      const { result } = renderHookWithStore()

      await act(async () => {
        await result.current.fetchMemoryById('mem_123')
      })

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'http://localhost:8765/api/v1/memories/mem_123?user_id=test_user'
      )
    })

    it('should handle empty memory ID', async () => {
      const { result } = renderHookWithStore()

      await act(async () => {
        await result.current.fetchMemoryById('')
      })

      expect(mockedAxios.get).not.toHaveBeenCalled()
    })

    it('should handle fetch memory by ID error', async () => {
      const errorMessage = 'Memory not found'
      mockedAxios.get.mockRejectedValueOnce(new Error(errorMessage))

      const { result } = renderHookWithStore()

      await act(async () => {
        await expect(result.current.fetchMemoryById('nonexistent')).rejects.toThrow(errorMessage)
      })

      expect(result.current.error).toBe(errorMessage)
    })
  })

  describe('updateMemory', () => {
    it('should update memory successfully', async () => {
      mockedAxios.put.mockResolvedValueOnce({ data: {} })

      const { result } = renderHookWithStore()

      await act(async () => {
        await result.current.updateMemory('mem_123', 'Updated content')
      })

      expect(mockedAxios.put).toHaveBeenCalledWith(
        'http://localhost:8765/api/v1/memories/mem_123',
        {
          memory_id: 'mem_123',
          memory_content: 'Updated content',
          user_id: 'test_user'
        }
      )

      expect(result.current.hasUpdates).toBeGreaterThan(0)
    })

    it('should handle empty memory ID', async () => {
      const { result } = renderHookWithStore()

      await act(async () => {
        await result.current.updateMemory('', 'content')
      })

      expect(mockedAxios.put).not.toHaveBeenCalled()
    })
  })

  describe('updateMemoryState', () => {
    it('should update memory state successfully', async () => {
      mockedAxios.post.mockResolvedValueOnce({ data: {} })

      const store = createTestStore()
      // Add memories to store
      store.dispatch({
        type: 'memories/setMemoriesSuccess',
        payload: [
          { id: 'mem1', memory: 'Memory 1', state: 'active' },
          { id: 'mem2', memory: 'Memory 2', state: 'active' }
        ]
      })

      const { result } = renderHookWithStore(store)

      await act(async () => {
        await result.current.updateMemoryState(['mem1'], 'paused')
      })

      expect(mockedAxios.post).toHaveBeenCalledWith(
        'http://localhost:8765/api/v1/memories/actions/pause',
        {
          memory_ids: ['mem1'],
          all_for_app: true,
          state: 'paused',
          user_id: 'test_user'
        }
      )

      // Check that memory state was updated in store
      const state = store.getState()
      const updatedMemory = state.memories.memories.find(m => m.id === 'mem1')
      expect(updatedMemory?.state).toBe('paused')
    })

    it('should handle archive state by removing from store', async () => {
      mockedAxios.post.mockResolvedValueOnce({ data: {} })

      const store = createTestStore()
      store.dispatch({
        type: 'memories/setMemoriesSuccess',
        payload: [
          { id: 'mem1', memory: 'Memory 1', state: 'active' },
          { id: 'mem2', memory: 'Memory 2', state: 'active' }
        ]
      })

      const { result } = renderHookWithStore(store)

      await act(async () => {
        await result.current.updateMemoryState(['mem1'], 'archived')
      })

      // Check that archived memory was removed from store
      const state = store.getState()
      expect(state.memories.memories).toHaveLength(1)
      expect(state.memories.memories[0].id).toBe('mem2')
    })

    it('should handle empty memory IDs array', async () => {
      const { result } = renderHookWithStore()

      await act(async () => {
        await result.current.updateMemoryState([], 'paused')
      })

      expect(mockedAxios.post).not.toHaveBeenCalled()
    })
  })

  describe('fetchAccessLogs', () => {
    it('should fetch access logs successfully', async () => {
      const mockAccessLogs = {
        logs: [
          { id: 'log1', timestamp: '2024-01-01', action: 'read' },
          { id: 'log2', timestamp: '2024-01-02', action: 'update' }
        ]
      }

      mockedAxios.get.mockResolvedValueOnce({ data: mockAccessLogs })

      const { result } = renderHookWithStore()

      await act(async () => {
        await result.current.fetchAccessLogs('mem_123', 1, 10)
      })

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'http://localhost:8765/api/v1/memories/mem_123/access-log?page=1&page_size=10'
      )
    })

    it('should handle empty memory ID', async () => {
      const { result } = renderHookWithStore()

      await act(async () => {
        await result.current.fetchAccessLogs('', 1, 10)
      })

      expect(mockedAxios.get).not.toHaveBeenCalled()
    })
  })

  describe('fetchRelatedMemories', () => {
    it('should fetch related memories successfully', async () => {
      const mockRelatedMemories = {
        items: [
          {
            id: 'related1',
            content: 'Related memory 1',
            created_at: 1640995200000,
            state: 'active',
            metadata_: {},
            categories: ['related'],
            app_name: 'test_app'
          }
        ]
      }

      mockedAxios.get.mockResolvedValueOnce({ data: mockRelatedMemories })

      const { result } = renderHookWithStore()

      await act(async () => {
        await result.current.fetchRelatedMemories('mem_123')
      })

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'http://localhost:8765/api/v1/memories/mem_123/related?user_id=test_user'
      )
    })

    it('should handle empty memory ID', async () => {
      const { result } = renderHookWithStore()

      await act(async () => {
        await result.current.fetchRelatedMemories('')
      })

      expect(mockedAxios.get).not.toHaveBeenCalled()
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      const networkError = new Error('Network Error')
      networkError.name = 'NetworkError'
      mockedAxios.post.mockRejectedValueOnce(networkError)

      const { result } = renderHookWithStore()

      await act(async () => {
        await expect(result.current.fetchMemories()).rejects.toThrow('Network Error')
      })

      expect(result.current.error).toBe('Network Error')
      expect(result.current.isLoading).toBe(false)
    })

    it('should handle timeout errors', async () => {
      const timeoutError = new Error('Timeout')
      timeoutError.name = 'TimeoutError'
      mockedAxios.post.mockRejectedValueOnce(timeoutError)

      const { result } = renderHookWithStore()

      await act(async () => {
        await expect(result.current.fetchMemories()).rejects.toThrow('Timeout')
      })

      expect(result.current.error).toBe('Timeout')
    })

    it('should handle API error responses', async () => {
      const apiError = {
        response: {
          status: 400,
          data: { detail: 'Invalid request' }
        },
        message: 'Request failed with status code 400'
      }
      mockedAxios.post.mockRejectedValueOnce(apiError)

      const { result } = renderHookWithStore()

      await act(async () => {
        await expect(result.current.fetchMemories()).rejects.toThrow('Request failed with status code 400')
      })
    })
  })

  describe('State Management Integration', () => {
    it('should update Redux store correctly', async () => {
      mockedAxios.post.mockResolvedValueOnce({ data: mockApiResponse })

      const store = createTestStore()
      const { result } = renderHookWithStore(store)

      await act(async () => {
        await result.current.fetchMemories()
      })

      const state = store.getState()
      expect(state.memories.memories).toHaveLength(1)
      expect(state.memories.memories[0].memory).toBe('Test memory content')
    })

    it('should handle selectedMemory updates correctly', async () => {
      const store = createTestStore()
      // Set a selected memory
      store.dispatch({
        type: 'memories/setSelectedMemory',
        payload: { id: 'mem1', text: 'Original content', state: 'active' }
      })

      mockedAxios.post.mockResolvedValueOnce({ data: {} })

      const { result } = renderHookWithStore(store)

      await act(async () => {
        await result.current.updateMemoryState(['mem1'], 'paused')
      })

      const state = store.getState()
      expect(state.memories.selectedMemory?.state).toBe('paused')
    })
  })

  describe('Data Transformation', () => {
    it('should transform API response to Memory objects correctly', async () => {
      const apiResponse = {
        items: [{
          id: 'mem_123',
          content: 'Test content',
          created_at: '2024-01-01T00:00:00Z',
          state: 'active',
          metadata_: { priority: 'high' },
          categories: ['work', 'urgent'],
          app_name: 'test_app'
        }],
        total: 1,
        pages: 1
      }

      mockedAxios.post.mockResolvedValueOnce({ data: apiResponse })

      const { result } = renderHookWithStore()

      await act(async () => {
        const response = await result.current.fetchMemories()
        const memory = response.memories[0]

        expect(memory.id).toBe('mem_123')
        expect(memory.memory).toBe('Test content')
        expect(memory.created_at).toBeInstanceOf(Number)
        expect(memory.state).toBe('active')
        expect(memory.metadata).toEqual({ priority: 'high' })
        expect(memory.categories).toEqual(['work', 'urgent'])
        expect(memory.client).toBe('api')
        expect(memory.app_name).toBe('test_app')
      })
    })
  })

  describe('Performance and Edge Cases', () => {
    it('should handle concurrent API calls', async () => {
      mockedAxios.post.mockResolvedValue({ data: mockApiResponse })
      mockedAxios.get.mockResolvedValue({ data: mockSimpleMemory })

      const { result } = renderHookWithStore()

      await act(async () => {
        // Make multiple concurrent calls
        const promises = [
          result.current.fetchMemories('query1'),
          result.current.fetchMemories('query2'),
          result.current.fetchMemoryById('mem1'),
          result.current.fetchMemoryById('mem2')
        ]

        await Promise.all(promises)
      })

      expect(mockedAxios.post).toHaveBeenCalledTimes(2)
      expect(mockedAxios.get).toHaveBeenCalledTimes(2)
    })

    it('should handle rapid successive calls', async () => {
      mockedAxios.post.mockResolvedValue({ data: mockApiResponse })

      const { result } = renderHookWithStore()

      await act(async () => {
        // Make rapid successive calls
        for (let i = 0; i < 5; i++) {
          result.current.fetchMemories(`query${i}`)
        }
      })

      // Should handle all calls without errors
      expect(result.current.error).toBeNull()
    })

    it('should handle large datasets', async () => {
      const largeDataset = {
        items: Array.from({ length: 1000 }, (_, i) => ({
          ...mockMemoryData,
          id: `mem_${i}`,
          content: `Memory ${i}`
        })),
        total: 1000,
        pages: 100
      }

      mockedAxios.post.mockResolvedValueOnce({ data: largeDataset })

      const { result } = renderHookWithStore()

      await act(async () => {
        const response = await result.current.fetchMemories()
        expect(response.memories).toHaveLength(1000)
        expect(response.total).toBe(1000)
      })
    })
  })
})
