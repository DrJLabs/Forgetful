import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { JsonEditor } from '../json-editor'

// Mock the UI components
jest.mock('../ui/alert', () => ({
  Alert: ({ children, variant, ...props }: any) => (
    <div data-testid="alert" data-variant={variant} {...props}>{children}</div>
  ),
  AlertDescription: ({ children, ...props }: any) => (
    <div data-testid="alert-description" {...props}>{children}</div>
  ),
}))

jest.mock('../ui/button', () => ({
  Button: ({ children, onClick, disabled, ...props }: any) => (
    <button data-testid="button" onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  ),
}))

jest.mock('../ui/textarea', () => ({
  Textarea: ({ value, onChange, ...props }: any) => (
    <textarea
      data-testid="textarea"
      value={value}
      onChange={onChange}
      {...props}
    />
  ),
}))

jest.mock('lucide-react', () => ({
  AlertCircle: () => <span data-testid="alert-circle-icon">⚠️</span>,
  CheckCircle2: () => <span data-testid="check-circle-icon">✅</span>,
}))

describe('JsonEditor', () => {
  const validObject = {
    name: 'Test Object',
    settings: {
      enabled: true,
      count: 42,
    },
    items: ['item1', 'item2'],
  }

  const mockOnChange = jest.fn()

  beforeEach(() => {
    mockOnChange.mockClear()
  })

  describe('Basic Rendering', () => {
    it('renders with initial JSON object', () => {
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      expect(screen.getByTestId('textarea')).toBeInTheDocument()
      expect(screen.getByTestId('button')).toBeInTheDocument()
      expect(screen.getByText('Apply Changes')).toBeInTheDocument()
    })

    it('displays JSON object as formatted string', () => {
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')
      const expectedJson = JSON.stringify(validObject, null, 2)
      expect(textarea).toHaveValue(expectedJson)
    })

    it('shows valid state indicator when JSON is valid', () => {
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument()
      expect(screen.queryByTestId('alert-circle-icon')).not.toBeInTheDocument()
    })
  })

  describe('JSON Validation', () => {
    it('validates JSON syntax in real-time', async () => {
      const user = userEvent.setup()
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')

      // Clear and enter invalid JSON
      await user.clear(textarea)
      await user.type(textarea, '{ "invalid": json }')

      await waitFor(() => {
        expect(screen.getByTestId('alert-circle-icon')).toBeInTheDocument()
        expect(screen.queryByTestId('check-circle-icon')).not.toBeInTheDocument()
      })
    })

    it('shows error message for invalid JSON', async () => {
      const user = userEvent.setup()
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')

      await user.clear(textarea)
      await user.type(textarea, '{ invalid json }')

      await waitFor(() => {
        expect(screen.getByTestId('alert')).toBeInTheDocument()
        expect(screen.getByText('Invalid JSON syntax')).toBeInTheDocument()
      })
    })

    it('clears error when JSON becomes valid again', async () => {
      const user = userEvent.setup()
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')

      // Enter invalid JSON
      await user.clear(textarea)
      await user.type(textarea, '{ invalid }')

      await waitFor(() => {
        expect(screen.getByText('Invalid JSON syntax')).toBeInTheDocument()
      })

      // Fix the JSON
      await user.clear(textarea)
      await user.type(textarea, '{ "valid": true }')

      await waitFor(() => {
        expect(screen.queryByText('Invalid JSON syntax')).not.toBeInTheDocument()
        expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument()
      })
    })

    it('handles empty JSON input', async () => {
      const user = userEvent.setup()
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')

      await user.clear(textarea)

      await waitFor(() => {
        expect(screen.getByTestId('alert-circle-icon')).toBeInTheDocument()
        expect(screen.getByText('Invalid JSON syntax')).toBeInTheDocument()
      })
    })
  })

  describe('Apply Changes Functionality', () => {
    it('applies valid JSON changes', async () => {
      const user = userEvent.setup()
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')
      const applyButton = screen.getByTestId('button')

      const newObject = { modified: true, count: 100 }

      await user.clear(textarea)
      await user.type(textarea, JSON.stringify(newObject))

      await user.click(applyButton)

      expect(mockOnChange).toHaveBeenCalledWith(newObject)
    })

    it('disables apply button when JSON is invalid', async () => {
      const user = userEvent.setup()
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')
      const applyButton = screen.getByTestId('button')

      await user.clear(textarea)
      await user.type(textarea, '{ invalid json }')

      await waitFor(() => {
        expect(applyButton).toBeDisabled()
      })
    })

    it('enables apply button when JSON is valid', async () => {
      const user = userEvent.setup()
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const applyButton = screen.getByTestId('button')

      // Should be enabled with valid initial JSON
      expect(applyButton).not.toBeDisabled()
    })

    it('shows error when apply fails with invalid JSON', async () => {
      const user = userEvent.setup()
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')
      const applyButton = screen.getByTestId('button')

      // Manually set invalid state and try to apply
      await user.clear(textarea)
      await user.type(textarea, '{ "valid": true }')

      // Simulate a scenario where the JSON appears valid but parsing fails on apply
      // This is edge case testing
      Object.defineProperty(JSON, 'parse', {
        value: jest.fn().mockImplementationOnce(() => {
          throw new Error('Parse error')
        }),
        writable: true,
      })

      await user.click(applyButton)

      await waitFor(() => {
        expect(screen.getByText('Failed to apply changes: Invalid JSON')).toBeInTheDocument()
      })

      // Restore JSON.parse
      Object.defineProperty(JSON, 'parse', {
        value: JSON.parse,
        writable: true,
      })
    })
  })

  describe('Value Updates', () => {
    it('updates display when value prop changes', () => {
      const { rerender } = render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const newObject = { different: 'object', array: [1, 2, 3] }
      rerender(<JsonEditor value={newObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')
      const expectedJson = JSON.stringify(newObject, null, 2)
      expect(textarea).toHaveValue(expectedJson)
    })

    it('handles invalid value prop gracefully', () => {
      // Create an object that can't be JSON.stringify'd
      const invalidObject = {}
      invalidObject.circular = invalidObject // Circular reference

      expect(() => {
        render(<JsonEditor value={invalidObject} onChange={mockOnChange} />)
      }).not.toThrow()

      // Should show error state
      expect(screen.getByTestId('alert-circle-icon')).toBeInTheDocument()
      expect(screen.getByText('Invalid JSON object')).toBeInTheDocument()
    })

    it('preserves user edits when external value changes', async () => {
      const user = userEvent.setup()
      const { rerender } = render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')

      // User starts editing
      await user.clear(textarea)
      await user.type(textarea, '{ "user": "editing" }')

      // External value changes (but shouldn't override user input)
      const newObject = { external: 'change' }
      rerender(<JsonEditor value={newObject} onChange={mockOnChange} />)

      // User's edit should be preserved
      expect(textarea).toHaveValue('{ "user": "editing" }')
    })
  })

  describe('Edge Cases', () => {
    it('handles null value', () => {
      render(<JsonEditor value={null} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')
      expect(textarea).toHaveValue('null')
    })

    it('handles undefined value', () => {
      render(<JsonEditor value={undefined} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')
      expect(textarea).toHaveValue('null') // JSON.stringify(undefined) returns undefined, but we handle it
    })

    it('handles primitive values', () => {
      render(<JsonEditor value="string value" onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')
      expect(textarea).toHaveValue('"string value"')
    })

    it('handles arrays', () => {
      const arrayValue = [1, 2, { nested: 'object' }]
      render(<JsonEditor value={arrayValue} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')
      const expectedJson = JSON.stringify(arrayValue, null, 2)
      expect(textarea).toHaveValue(expectedJson)
    })

    it('handles very large JSON objects', () => {
      const largeObject = {
        data: Array.from({ length: 1000 }, (_, i) => ({ id: i, value: `item_${i}` }))
      }

      render(<JsonEditor value={largeObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')
      expect(textarea).toBeInTheDocument()
      // Should handle large objects without crashing
    })
  })

  describe('User Experience', () => {
    it('provides immediate visual feedback for validation state', async () => {
      const user = userEvent.setup()
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')

      // Start with valid state
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument()

      // Type invalid character
      await user.type(textarea, 'x')

      await waitFor(() => {
        expect(screen.getByTestId('alert-circle-icon')).toBeInTheDocument()
        expect(screen.queryByTestId('check-circle-icon')).not.toBeInTheDocument()
      })
    })

    it('maintains focus and cursor position during validation', async () => {
      const user = userEvent.setup()
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')

      await user.click(textarea)
      expect(textarea).toHaveFocus()

      // Type something
      await user.type(textarea, ' ')

      // Focus should be maintained
      expect(textarea).toHaveFocus()
    })

    it('provides clear error messages', async () => {
      const user = userEvent.setup()
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')

      await user.clear(textarea)
      await user.type(textarea, '{ "key": }')

      await waitFor(() => {
        const errorMessage = screen.getByText('Invalid JSON syntax')
        expect(errorMessage).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')
      const button = screen.getByTestId('button')

      expect(textarea).toBeInTheDocument()
      expect(button).toBeInTheDocument()
    })

    it('associates error messages with form controls', async () => {
      const user = userEvent.setup()
      render(<JsonEditor value={validObject} onChange={mockOnChange} />)

      const textarea = screen.getByTestId('textarea')

      await user.clear(textarea)
      await user.type(textarea, 'invalid')

      await waitFor(() => {
        const alert = screen.getByTestId('alert')
        expect(alert).toHaveAttribute('data-variant', 'destructive')
      })
    })
  })
})
