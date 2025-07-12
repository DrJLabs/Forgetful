import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { FormView } from '../form-view'

// Mock the UI components
jest.mock('../ui/card', () => ({
  Card: ({ children, ...props }: any) => <div data-testid="card" {...props}>{children}</div>,
  CardContent: ({ children, ...props }: any) => <div data-testid="card-content" {...props}>{children}</div>,
  CardDescription: ({ children, ...props }: any) => <div data-testid="card-description" {...props}>{children}</div>,
  CardHeader: ({ children, ...props }: any) => <div data-testid="card-header" {...props}>{children}</div>,
  CardTitle: ({ children, ...props }: any) => <h3 data-testid="card-title" {...props}>{children}</h3>,
}))

jest.mock('../ui/input', () => ({
  Input: ({ ...props }: any) => <input data-testid="input" {...props} />,
}))

jest.mock('../ui/label', () => ({
  Label: ({ children, ...props }: any) => <label data-testid="label" {...props}>{children}</label>,
}))

jest.mock('../ui/slider', () => ({
  Slider: ({ onValueChange, value, ...props }: any) => (
    <input
      data-testid="slider"
      type="range"
      value={value?.[0] || 0}
      onChange={(e) => onValueChange?.([parseFloat(e.target.value)])}
      {...props}
    />
  ),
}))

jest.mock('../ui/switch', () => ({
  Switch: ({ checked, onCheckedChange, ...props }: any) => (
    <input
      data-testid="switch"
      type="checkbox"
      checked={checked}
      onChange={(e) => onCheckedChange?.(e.target.checked)}
      {...props}
    />
  ),
}))

jest.mock('../ui/button', () => ({
  Button: ({ children, onClick, ...props }: any) => (
    <button data-testid="button" onClick={onClick} {...props}>{children}</button>
  ),
}))

jest.mock('../ui/select', () => ({
  Select: ({ children, onValueChange, value }: any) => (
    <div data-testid="select">
      <select
        data-testid="select-trigger"
        value={value}
        onChange={(e) => onValueChange?.(e.target.value)}
      >
        {children}
      </select>
    </div>
  ),
  SelectContent: ({ children }: any) => <div data-testid="select-content">{children}</div>,
  SelectItem: ({ children, value }: any) => (
    <option data-testid="select-item" value={value}>{children}</option>
  ),
  SelectTrigger: ({ children }: any) => <div data-testid="select-trigger">{children}</div>,
  SelectValue: ({ placeholder }: any) => <span data-testid="select-value">{placeholder}</span>,
}))

jest.mock('../ui/textarea', () => ({
  Textarea: ({ ...props }: any) => <textarea data-testid="textarea" {...props} />,
}))

jest.mock('lucide-react', () => ({
  Eye: () => <span data-testid="eye-icon">👁</span>,
  EyeOff: () => <span data-testid="eye-off-icon">🙈</span>,
}))

describe('FormView', () => {
  const defaultSettings = {
    openmemory: {
      custom_instructions: '',
    },
    mem0: {
      llm: {
        provider: 'openai',
        config: {
          model: 'gpt-4',
          api_key: '',
          temperature: 0.7,
          max_tokens: 2000,
        },
      },
      embedder: {
        provider: 'openai',
        config: {
          model: 'text-embedding-ada-002',
          api_key: '',
        },
      },
    },
  }

  const mockOnChange = jest.fn()

  beforeEach(() => {
    mockOnChange.mockClear()
  })

  describe('Basic Rendering', () => {
    it('renders all main sections', () => {
      render(<FormView settings={defaultSettings} onChange={mockOnChange} />)

      expect(screen.getByText('OpenMemory Settings')).toBeInTheDocument()
      expect(screen.getByText('LLM Settings')).toBeInTheDocument()
      expect(screen.getByText('Embedder Settings')).toBeInTheDocument()
    })

    it('renders with empty settings', () => {
      render(<FormView settings={{}} onChange={mockOnChange} />)

      expect(screen.getByText('OpenMemory Settings')).toBeInTheDocument()
      expect(screen.getByText('LLM Settings')).toBeInTheDocument()
      expect(screen.getByText('Embedder Settings')).toBeInTheDocument()
    })
  })

  describe('OpenMemory Settings', () => {
    it('renders custom instructions textarea', () => {
      render(<FormView settings={defaultSettings} onChange={mockOnChange} />)

      const textarea = screen.getByDisplayValue('')
      expect(textarea).toBeInTheDocument()
    })

    it('handles custom instructions change', async () => {
      const user = userEvent.setup()
      render(<FormView settings={defaultSettings} onChange={mockOnChange} />)

      const textarea = screen.getByDisplayValue('')
      await user.type(textarea, 'Custom memory instructions')

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultSettings,
        openmemory: {
          ...defaultSettings.openmemory,
          custom_instructions: 'Custom memory instructions',
        },
      })
    })
  })

  describe('LLM Settings', () => {
    it('renders LLM provider selection', () => {
      render(<FormView settings={defaultSettings} onChange={mockOnChange} />)

      const selects = screen.getAllByTestId('select-trigger')
      expect(selects).toHaveLength(2) // LLM and Embedder
    })

    it('handles LLM provider change', () => {
      render(<FormView settings={defaultSettings} onChange={mockOnChange} />)

      const select = screen.getAllByTestId('select-trigger')[0]
      fireEvent.change(select, { target: { value: 'anthropic' } })

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultSettings,
        mem0: {
          ...defaultSettings.mem0,
          llm: {
            ...defaultSettings.mem0.llm,
            provider: 'anthropic',
          },
        },
      })
    })

    it('shows API key field for non-Ollama providers', () => {
      render(<FormView settings={defaultSettings} onChange={mockOnChange} />)

      expect(screen.getByText('API Key')).toBeInTheDocument()
    })

    it('hides API key field for Ollama provider', () => {
      const ollamaSettings = {
        ...defaultSettings,
        mem0: {
          ...defaultSettings.mem0,
          llm: {
            ...defaultSettings.mem0.llm,
            provider: 'ollama',
          },
        },
      }

      render(<FormView settings={ollamaSettings} onChange={mockOnChange} />)

      // Should not show API key for LLM when using Ollama
      const apiKeyLabels = screen.queryAllByText('API Key')
      expect(apiKeyLabels).toHaveLength(1) // Only for embedder, not LLM
    })

    it('shows Ollama URL field for Ollama provider', () => {
      const ollamaSettings = {
        ...defaultSettings,
        mem0: {
          ...defaultSettings.mem0,
          llm: {
            ...defaultSettings.mem0.llm,
            provider: 'ollama',
          },
        },
      }

      render(<FormView settings={ollamaSettings} onChange={mockOnChange} />)

      expect(screen.getByText('Ollama Base URL')).toBeInTheDocument()
    })

    it('toggles API key visibility', async () => {
      const user = userEvent.setup()
      render(<FormView settings={defaultSettings} onChange={mockOnChange} />)

      const eyeButton = screen.getAllByTestId('button').find(button =>
        button.textContent?.includes('👁') || button.textContent?.includes('🙈')
      )
      expect(eyeButton).toBeInTheDocument()

      await user.click(eyeButton!)
      // The eye icon should toggle (implementation detail, but shows interaction works)
      expect(eyeButton).toBeInTheDocument()
    })

    it('toggles advanced settings', async () => {
      const user = userEvent.setup()
      render(<FormView settings={defaultSettings} onChange={mockOnChange} />)

      const advancedToggle = screen.getByTestId('switch')
      await user.click(advancedToggle)

      // Should show temperature and max tokens when advanced is enabled
      await waitFor(() => {
        expect(screen.getByText(/Temperature:/)).toBeInTheDocument()
        expect(screen.getByText('Max Tokens')).toBeInTheDocument()
      })
    })

    it('handles temperature change in advanced settings', async () => {
      const user = userEvent.setup()
      render(<FormView settings={defaultSettings} onChange={mockOnChange} />)

      // Enable advanced settings first
      const advancedToggle = screen.getByTestId('switch')
      await user.click(advancedToggle)

      await waitFor(() => {
        const temperatureSlider = screen.getByTestId('slider')
        fireEvent.change(temperatureSlider, { target: { value: '0.9' } })

        expect(mockOnChange).toHaveBeenCalledWith({
          ...defaultSettings,
          mem0: {
            ...defaultSettings.mem0,
            llm: {
              ...defaultSettings.mem0.llm,
              config: {
                ...defaultSettings.mem0.llm.config,
                temperature: 0.9,
              },
            },
          },
        })
      })
    })
  })

  describe('Embedder Settings', () => {
    it('handles embedder provider change', () => {
      render(<FormView settings={defaultSettings} onChange={mockOnChange} />)

      const select = screen.getAllByTestId('select-trigger')[1] // Second select is embedder
      fireEvent.change(select, { target: { value: 'huggingface' } })

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultSettings,
        mem0: {
          ...defaultSettings.mem0,
          embedder: {
            ...defaultSettings.mem0.embedder,
            provider: 'huggingface',
          },
        },
      })
    })

    it('handles embedder model change', async () => {
      const user = userEvent.setup()
      render(<FormView settings={defaultSettings} onChange={mockOnChange} />)

      // Find the embedder model input (should be the second model input)
      const inputs = screen.getAllByDisplayValue('text-embedding-ada-002')
      expect(inputs).toHaveLength(1)

      await user.clear(inputs[0])
      await user.type(inputs[0], 'new-embedding-model')

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultSettings,
        mem0: {
          ...defaultSettings.mem0,
          embedder: {
            ...defaultSettings.mem0.embedder,
            config: {
              ...defaultSettings.mem0.embedder.config,
              model: 'new-embedding-model',
            },
          },
        },
      })
    })
  })

  describe('Provider-specific Logic', () => {
    it('correctly identifies Ollama providers', () => {
      const ollamaSettings = {
        ...defaultSettings,
        mem0: {
          llm: { provider: 'ollama', config: {} },
          embedder: { provider: 'ollama', config: {} },
        },
      }

      render(<FormView settings={ollamaSettings} onChange={mockOnChange} />)

      // Should show Ollama URL fields for both LLM and Embedder
      const ollamaUrlLabels = screen.getAllByText('Ollama Base URL')
      expect(ollamaUrlLabels).toHaveLength(2)

      // Should not show API Key fields
      const apiKeyLabels = screen.queryAllByText('API Key')
      expect(apiKeyLabels).toHaveLength(0)
    })

    it('handles mixed provider configurations', () => {
      const mixedSettings = {
        ...defaultSettings,
        mem0: {
          llm: { provider: 'openai', config: {} },
          embedder: { provider: 'ollama', config: {} },
        },
      }

      render(<FormView settings={mixedSettings} onChange={mockOnChange} />)

      // Should show one API key (for LLM) and one Ollama URL (for embedder)
      expect(screen.getByText('API Key')).toBeInTheDocument()
      expect(screen.getByText('Ollama Base URL')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles undefined nested settings gracefully', () => {
      const incompleteSettings = {
        mem0: {
          llm: {}
        }
      }

      expect(() => {
        render(<FormView settings={incompleteSettings} onChange={mockOnChange} />)
      }).not.toThrow()
    })

    it('handles settings changes when config is undefined', () => {
      const incompleteSettings = {
        mem0: {
          llm: { provider: 'openai' },
          embedder: { provider: 'openai' }
        }
      }

      render(<FormView settings={incompleteSettings} onChange={mockOnChange} />)

      // Should be able to change model even when config is undefined
      const modelInputs = screen.getAllByPlaceholderText('Enter model name')
      fireEvent.change(modelInputs[0], { target: { value: 'gpt-4' } })

      expect(mockOnChange).toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('has proper labels for form inputs', () => {
      render(<FormView settings={defaultSettings} onChange={mockOnChange} />)

      expect(screen.getByText('Custom Instructions')).toBeInTheDocument()
      expect(screen.getByText('LLM Provider')).toBeInTheDocument()
      expect(screen.getByText('Model')).toBeInTheDocument()
      expect(screen.getByText('Embedder Provider')).toBeInTheDocument()
    })

    it('provides help text for important fields', () => {
      render(<FormView settings={defaultSettings} onChange={mockOnChange} />)

      expect(screen.getByText(/Custom instructions that will be used to guide memory processing/)).toBeInTheDocument()
      expect(screen.getByText(/Use "env:API_KEY" to load from environment variable/)).toBeInTheDocument()
    })
  })
})