import { render, screen, fireEvent } from '@testing-library/react'
import { Button, buttonVariants } from '../button'

describe('Button', () => {
  describe('Basic Rendering', () => {
    it('renders button with text', () => {
      render(<Button>Click me</Button>)
      expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
    })

    it('renders button with default variant and size', () => {
      render(<Button>Default Button</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-primary', 'text-primary-foreground', 'h-10', 'px-4', 'py-2')
    })

    it('forwards ref correctly', () => {
      const ref = React.createRef<HTMLButtonElement>()
      render(<Button ref={ref}>Button with ref</Button>)
      expect(ref.current).toBeInstanceOf(HTMLButtonElement)
    })
  })

  describe('Variants', () => {
    it('renders default variant correctly', () => {
      render(<Button variant="default">Default</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-primary', 'text-primary-foreground', 'hover:bg-primary/90')
    })

    it('renders destructive variant correctly', () => {
      render(<Button variant="destructive">Destructive</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-destructive', 'text-destructive-foreground', 'hover:bg-destructive/90')
    })

    it('renders outline variant correctly', () => {
      render(<Button variant="outline">Outline</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('border', 'border-input', 'bg-background', 'hover:bg-accent', 'hover:text-accent-foreground')
    })

    it('renders secondary variant correctly', () => {
      render(<Button variant="secondary">Secondary</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-secondary', 'text-secondary-foreground', 'hover:bg-secondary/80')
    })

    it('renders ghost variant correctly', () => {
      render(<Button variant="ghost">Ghost</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('hover:bg-accent', 'hover:text-accent-foreground')
    })

    it('renders link variant correctly', () => {
      render(<Button variant="link">Link</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('text-primary', 'underline-offset-4', 'hover:underline')
    })
  })

  describe('Sizes', () => {
    it('renders default size correctly', () => {
      render(<Button size="default">Default Size</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('h-10', 'px-4', 'py-2')
    })

    it('renders small size correctly', () => {
      render(<Button size="sm">Small</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('h-9', 'rounded-md', 'px-3')
    })

    it('renders large size correctly', () => {
      render(<Button size="lg">Large</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('h-11', 'rounded-md', 'px-8')
    })

    it('renders icon size correctly', () => {
      render(<Button size="icon">Icon</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('h-10', 'w-10')
    })
  })

  describe('Props and Attributes', () => {
    it('handles onClick events', () => {
      const handleClick = jest.fn()
      render(<Button onClick={handleClick}>Clickable</Button>)

      fireEvent.click(screen.getByRole('button'))
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('handles disabled state', () => {
      const handleClick = jest.fn()
      render(<Button disabled onClick={handleClick}>Disabled</Button>)

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
      expect(button).toHaveClass('disabled:pointer-events-none', 'disabled:opacity-50')

      fireEvent.click(button)
      expect(handleClick).not.toHaveBeenCalled()
    })

    it('accepts custom className', () => {
      render(<Button className="custom-class">Custom Class</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('custom-class')
    })

    it('accepts custom attributes', () => {
      render(<Button data-testid="custom-button" aria-label="Custom Button">Test</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('data-testid', 'custom-button')
      expect(button).toHaveAttribute('aria-label', 'Custom Button')
    })

    it('accepts type attribute', () => {
      render(<Button type="submit">Submit</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('type', 'submit')
    })
  })

  describe('AsChild Functionality', () => {
    it('renders as child component when asChild is true', () => {
      render(
        <Button asChild>
          <a href="/test">Link Button</a>
        </Button>
      )

      const link = screen.getByRole('link')
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/test')
      expect(link).toHaveClass('inline-flex', 'items-center', 'justify-center')
    })

    it('maintains button classes when used as child', () => {
      render(
        <Button asChild variant="outline" size="lg">
          <a href="/test">Outline Link</a>
        </Button>
      )

      const link = screen.getByRole('link')
      expect(link).toHaveClass('border', 'border-input', 'h-11', 'rounded-md', 'px-8')
    })
  })

  describe('Accessibility', () => {
    it('has proper focus styles', () => {
      render(<Button>Focusable</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('focus-visible:outline-none', 'focus-visible:ring-2', 'focus-visible:ring-ring', 'focus-visible:ring-offset-2')
    })

    it('supports keyboard navigation', () => {
      const handleClick = jest.fn()
      render(<Button onClick={handleClick}>Keyboard Button</Button>)

      const button = screen.getByRole('button')
      button.focus()

      fireEvent.keyDown(button, { key: 'Enter' })
      expect(handleClick).toHaveBeenCalledTimes(1)

      fireEvent.keyDown(button, { key: ' ' })
      expect(handleClick).toHaveBeenCalledTimes(2)
    })
  })

  describe('CSS Classes', () => {
    it('has base CSS classes', () => {
      render(<Button>Base Classes</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass(
        'inline-flex',
        'items-center',
        'justify-center',
        'gap-2',
        'whitespace-nowrap',
        'rounded-md',
        'text-sm',
        'font-medium',
        'ring-offset-background',
        'transition-colors'
      )
    })

    it('has SVG styling classes', () => {
      render(<Button>SVG Button</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('[&_svg]:pointer-events-none', '[&_svg]:size-4', '[&_svg]:shrink-0')
    })
  })

  describe('ButtonVariants Function', () => {
    it('returns correct classes for variant combinations', () => {
      const defaultClasses = buttonVariants()
      expect(defaultClasses).toContain('bg-primary')
      expect(defaultClasses).toContain('h-10')

      const outlineSmallClasses = buttonVariants({ variant: 'outline', size: 'sm' })
      expect(outlineSmallClasses).toContain('border')
      expect(outlineSmallClasses).toContain('h-9')

      const ghostLargeClasses = buttonVariants({ variant: 'ghost', size: 'lg' })
      expect(ghostLargeClasses).toContain('hover:bg-accent')
      expect(ghostLargeClasses).toContain('h-11')
    })
  })
})

// Additional React import for ref testing
import * as React from 'react'