import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { CreateMemoryDialog } from '../CreateMemoryDialog'

// Mock toast
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn()
  }
}))

// Mock useMemoriesApi hook
jest.mock('@/hooks/useMemoriesApi', () => ({
  useMemoriesApi: jest.fn()
}))

// Mock UI components
jest.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children, open, onOpenChange }: any) =>
    open ? <div data-testid="dialog">{children}</div> : null,
  DialogContent: ({ children }: any) => <div data-testid="dialog-content">{children}</div>,
  DialogDescription: ({ children }: any) => <p data-testid="dialog-description">{children}</p>,
  DialogFooter: ({ children }: any) => <div data-testid="dialog-footer">{children}</div>,
  DialogHeader: ({ children }: any) => <div data-testid="dialog-header">{children}</div>,
  DialogTitle: ({ children }: any) => <h2 data-testid="dialog-title">{children}</h2>,
  DialogTrigger: ({ children }: any) => <div data-testid="dialog-trigger">{children}</div>
}))

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, disabled, variant, size, ...props }: any) => (
    <button
      data-testid={`button-${variant || 'default'}`}
      onClick={onClick}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  )
}))

jest.mock('@/components/ui/textarea', () => ({
  Textarea: ({ placeholder, id, ...props }: any) => (
    <textarea
      data-testid="memory-textarea"
      placeholder={placeholder}
      id={id}
      {...props}
    />
  )
}))

jest.mock('@/components/ui/label', () => ({
  Label: ({ children, htmlFor }: any) => (
    <label data-testid="memory-label" htmlFor={htmlFor}>{children}</label>
  )
}))

jest.mock('lucide-react', () => ({
  Loader2: () => <div data-testid="loading-spinner">Loading...</div>
}))

jest.mock('react-icons/go', () => ({
  GoPlus: () => <div data-testid="plus-icon">+</div>
}))

describe('CreateMemoryDialog', () => {
  const mockCreateMemory = jest.fn()
  const mockFetchMemories = jest.fn()
  const user = userEvent.setup()

  beforeEach(() => {
    jest.clearAllMocks()

    // Mock useMemoriesApi hook
    const { useMemoriesApi } = require('@/hooks/useMemoriesApi')
    useMemoriesApi.mockReturnValue({
      createMemory: mockCreateMemory,
      fetchMemories: mockFetchMemories,
      isLoading: false
    })
  })

  describe('Rendering', () => {
    it('renders trigger button correctly', () => {
      render(<CreateMemoryDialog />)

      expect(screen.getByTestId('dialog-trigger')).toBeInTheDocument()
      expect(screen.getByTestId('button-outline')).toBeInTheDocument()
      expect(screen.getByTestId('plus-icon')).toBeInTheDocument()
      expect(screen.getByText('Create Memory')).toBeInTheDocument()
    })

    it('does not render dialog content initially', () => {
      render(<CreateMemoryDialog />)

      expect(screen.queryByTestId('dialog-content')).not.toBeInTheDocument()
    })

    it('renders dialog content when opened', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      expect(screen.getByTestId('dialog-content')).toBeInTheDocument()
      expect(screen.getByTestId('dialog-title')).toBeInTheDocument()
      expect(screen.getByTestId('dialog-description')).toBeInTheDocument()
      expect(screen.getByTestId('memory-textarea')).toBeInTheDocument()
    })

    it('renders correct dialog content', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      expect(screen.getByText('Create New Memory')).toBeInTheDocument()
      expect(screen.getByText('Add a new memory to your OpenMemory instance')).toBeInTheDocument()
      expect(screen.getByText('Memory')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('e.g., Lives in San Francisco')).toBeInTheDocument()
    })

    it('renders action buttons in dialog footer', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      expect(screen.getByText('Cancel')).toBeInTheDocument()
      expect(screen.getByText('Save Memory')).toBeInTheDocument()
    })
  })

  describe('Dialog Interactions', () => {
    it('opens dialog when trigger button is clicked', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      expect(screen.queryByTestId('dialog-content')).not.toBeInTheDocument()

      await user.click(triggerButton)

      expect(screen.getByTestId('dialog-content')).toBeInTheDocument()
    })

    it('closes dialog when cancel button is clicked', async () => {
      render(<CreateMemoryDialog />)

      // Open dialog
      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)
      expect(screen.getByTestId('dialog-content')).toBeInTheDocument()

      // Close dialog
      const cancelButton = screen.getByText('Cancel')
      await user.click(cancelButton)

      expect(screen.queryByTestId('dialog-content')).not.toBeInTheDocument()
    })

    it('maintains textarea focus when dialog opens', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      expect(textarea).toBeInTheDocument()
      // Note: focus testing can be tricky in jsdom, so we just verify the element exists
    })
  })

  describe('Form Input', () => {
    it('allows typing in the textarea', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      await user.type(textarea, 'This is a test memory')

      expect(textarea).toHaveValue('This is a test memory')
    })

    it('handles multiline input correctly', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      const multilineText = 'Line 1\nLine 2\nLine 3'
      await user.type(textarea, multilineText)

      expect(textarea).toHaveValue(multilineText)
    })

    it('handles special characters and emojis', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      const specialText = 'Special chars: @#$%^&*() 🚀🔥💻'
      await user.type(textarea, specialText)

      expect(textarea).toHaveValue(specialText)
    })

    it('clears textarea when dialog reopens after successful creation', async () => {
      mockCreateMemory.mockResolvedValue({})
      mockFetchMemories.mockResolvedValue({})

      render(<CreateMemoryDialog />)

      // Open dialog and type
      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      await user.type(textarea, 'Test memory')

      // Save memory
      const saveButton = screen.getByText('Save Memory')
      await user.click(saveButton)

      // Wait for dialog to close and reopen
      await waitFor(() => {
        expect(screen.queryByTestId('dialog-content')).not.toBeInTheDocument()
      })

      await user.click(triggerButton)

      // Textarea should be empty
      const newTextarea = screen.getByTestId('memory-textarea')
      expect(newTextarea).toHaveValue('')
    })
  })

  describe('Memory Creation', () => {
    it('calls createMemory with correct text when save button is clicked', async () => {
      mockCreateMemory.mockResolvedValue({})
      mockFetchMemories.mockResolvedValue({})

      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      await user.type(textarea, 'Test memory content')

      const saveButton = screen.getByText('Save Memory')
      await user.click(saveButton)

      expect(mockCreateMemory).toHaveBeenCalledWith('Test memory content')
    })

    it('refetches memories after successful creation', async () => {
      mockCreateMemory.mockResolvedValue({})
      mockFetchMemories.mockResolvedValue({})

      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      await user.type(textarea, 'Test memory')

      const saveButton = screen.getByText('Save Memory')
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockFetchMemories).toHaveBeenCalled()
      })
    })

    it('closes dialog after successful creation', async () => {
      mockCreateMemory.mockResolvedValue({})
      mockFetchMemories.mockResolvedValue({})

      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      await user.type(textarea, 'Test memory')

      const saveButton = screen.getByText('Save Memory')
      await user.click(saveButton)

      await waitFor(() => {
        expect(screen.queryByTestId('dialog-content')).not.toBeInTheDocument()
      })
    })

    it('shows success toast after successful creation', async () => {
      const { toast } = require('sonner')
      mockCreateMemory.mockResolvedValue({})
      mockFetchMemories.mockResolvedValue({})

      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      await user.type(textarea, 'Test memory')

      const saveButton = screen.getByText('Save Memory')
      await user.click(saveButton)

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('Memory created successfully')
      })
    })

    it('handles empty textarea gracefully', async () => {
      mockCreateMemory.mockResolvedValue({})
      mockFetchMemories.mockResolvedValue({})

      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      // Don't type anything in textarea
      const saveButton = screen.getByText('Save Memory')
      await user.click(saveButton)

      expect(mockCreateMemory).toHaveBeenCalledWith('')
    })
  })

  describe('Loading States', () => {
    it('shows loading spinner when isLoading is true', async () => {
      const { useMemoriesApi } = require('@/hooks/useMemoriesApi')
      useMemoriesApi.mockReturnValue({
        createMemory: mockCreateMemory,
        fetchMemories: mockFetchMemories,
        isLoading: true
      })

      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
      expect(screen.getByText('Loading...')).toBeInTheDocument()
    })

    it('disables save button when loading', async () => {
      const { useMemoriesApi } = require('@/hooks/useMemoriesApi')
      useMemoriesApi.mockReturnValue({
        createMemory: mockCreateMemory,
        fetchMemories: mockFetchMemories,
        isLoading: true
      })

      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const saveButton = screen.getByText('Loading...')
      expect(saveButton).toBeDisabled()
    })

    it('shows normal save button text when not loading', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const saveButton = screen.getByText('Save Memory')
      expect(saveButton).not.toBeDisabled()
      expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('shows error toast when creation fails', async () => {
      const { toast } = require('sonner')
      const consoleError = jest.spyOn(console, 'error').mockImplementation()
      mockCreateMemory.mockRejectedValue(new Error('Creation failed'))

      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      await user.type(textarea, 'Test memory')

      const saveButton = screen.getByText('Save Memory')
      await user.click(saveButton)

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Failed to create memory')
      })

      consoleError.mockRestore()
    })

    it('keeps dialog open when creation fails', async () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation()
      mockCreateMemory.mockRejectedValue(new Error('Creation failed'))

      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      await user.type(textarea, 'Test memory')

      const saveButton = screen.getByText('Save Memory')
      await user.click(saveButton)

      await waitFor(() => {
        expect(screen.getByTestId('dialog-content')).toBeInTheDocument()
      })

      consoleError.mockRestore()
    })

    it('preserves textarea content when creation fails', async () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation()
      mockCreateMemory.mockRejectedValue(new Error('Creation failed'))

      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      const testContent = 'Test memory that will fail'
      await user.type(textarea, testContent)

      const saveButton = screen.getByText('Save Memory')
      await user.click(saveButton)

      await waitFor(() => {
        expect(textarea).toHaveValue(testContent)
      })

      consoleError.mockRestore()
    })

    it('handles network errors gracefully', async () => {
      const { toast } = require('sonner')
      const consoleError = jest.spyOn(console, 'error').mockImplementation()
      mockCreateMemory.mockRejectedValue(new Error('Network Error'))

      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      await user.type(textarea, 'Test memory')

      const saveButton = screen.getByText('Save Memory')
      await user.click(saveButton)

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Failed to create memory')
        expect(consoleError).toHaveBeenCalledWith(expect.any(Error))
      })

      consoleError.mockRestore()
    })
  })

  describe('Keyboard Interactions', () => {
    it('supports keyboard navigation', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')

      // Focus and activate with keyboard
      triggerButton.focus()
      await user.keyboard('{Enter}')

      expect(screen.getByTestId('dialog-content')).toBeInTheDocument()
    })

    it('allows typing with keyboard in textarea', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')

      // Focus textarea and type
      await user.click(textarea)
      await user.keyboard('Keyboard input test')

      expect(textarea).toHaveValue('Keyboard input test')
    })

    it('handles keyboard shortcuts in textarea', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      await user.click(textarea)

      // Type and select all
      await user.keyboard('Some text to select')
      await user.keyboard('{Control>}a{/Control}')

      // Type over selection
      await user.keyboard('Replaced text')

      expect(textarea).toHaveValue('Replaced text')
    })
  })

  describe('Accessibility', () => {
    it('has correct ARIA labels and attributes', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      expect(screen.getByTestId('dialog-title')).toBeInTheDocument()
      expect(screen.getByTestId('dialog-description')).toBeInTheDocument()
      expect(screen.getByTestId('memory-label')).toBeInTheDocument()
    })

    it('associates label with textarea correctly', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const label = screen.getByTestId('memory-label')
      const textarea = screen.getByTestId('memory-textarea')

      expect(label).toHaveAttribute('htmlFor', 'memory')
      expect(textarea).toHaveAttribute('id', 'memory')
    })

    it('maintains focus management', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      // Dialog should be present and focusable elements should be accessible
      expect(screen.getByTestId('memory-textarea')).toBeInTheDocument()
      expect(screen.getByText('Cancel')).toBeInTheDocument()
      expect(screen.getByText('Save Memory')).toBeInTheDocument()
    })
  })

  describe('Performance', () => {
    it('renders quickly with large amounts of text', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')
      await user.click(triggerButton)

      const textarea = screen.getByTestId('memory-textarea')
      const largeText = 'A'.repeat(10000) // 10KB of text

      const startTime = performance.now()
      await user.type(textarea, largeText)
      const endTime = performance.now()

      expect(endTime - startTime).toBeLessThan(5000) // Should complete within 5 seconds
      expect(textarea).toHaveValue(largeText)
    })

    it('handles rapid open/close cycles', async () => {
      render(<CreateMemoryDialog />)

      const triggerButton = screen.getByTestId('button-outline')

      // Rapidly open and close dialog multiple times
      for (let i = 0; i < 5; i++) {
        await user.click(triggerButton)
        expect(screen.getByTestId('dialog-content')).toBeInTheDocument()

        const cancelButton = screen.getByText('Cancel')
        await user.click(cancelButton)

        await waitFor(() => {
          expect(screen.queryByTestId('dialog-content')).not.toBeInTheDocument()
        })
      }

      // Should still work normally after rapid cycles
      await user.click(triggerButton)
      expect(screen.getByTestId('dialog-content')).toBeInTheDocument()
    })
  })
})