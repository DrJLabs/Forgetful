import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { Navbar } from '../Navbar'
import { usePathname } from 'next/navigation'

// Mock the hooks used in the component
jest.mock('@/hooks/useMemoriesApi', () => ({
  useMemoriesApi: () => ({
    fetchMemoryById: jest.fn(),
    fetchAccessLogs: jest.fn(),
    fetchRelatedMemories: jest.fn(),
    fetchMemories: jest.fn(),
  }),
}))

jest.mock('@/hooks/useAppsApi', () => ({
  useAppsApi: () => ({
    fetchAppMemories: jest.fn(),
    fetchAppAccessedMemories: jest.fn(),
    fetchAppDetails: jest.fn(),
    fetchApps: jest.fn(),
  }),
}))

jest.mock('@/hooks/useStats', () => ({
  useStats: () => ({
    fetchStats: jest.fn(),
  }),
}))

jest.mock('@/hooks/useConfig', () => ({
  useConfig: () => ({
    fetchConfig: jest.fn(),
  }),
}))

// Mock the CreateMemoryDialog component
jest.mock('@/app/memories/components/CreateMemoryDialog', () => ({
  CreateMemoryDialog: () => <div data-testid="create-memory-dialog">Create Memory</div>,
}))

// Mock next/navigation with a controllable pathname
const mockPush = jest.fn()
const mockPathname = jest.fn()

jest.mock('next/navigation', () => ({
  usePathname: () => mockPathname(),
  useRouter: () => ({
    push: mockPush,
  }),
}))

describe('Navbar', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockPathname.mockReturnValue('/')
  })

  describe('Rendering', () => {
    it('renders the main navigation elements', () => {
      render(<Navbar />)
      
      // Check logo and title
      expect(screen.getByAltText('OpenMemory')).toBeInTheDocument()
      expect(screen.getByText('OpenMemory')).toBeInTheDocument()
      
      // Check navigation links
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
      expect(screen.getByText('Memories')).toBeInTheDocument()
      expect(screen.getByText('Apps')).toBeInTheDocument()
      expect(screen.getByText('Settings')).toBeInTheDocument()
      
      // Check action buttons
      expect(screen.getByText('Refresh')).toBeInTheDocument()
      expect(screen.getByTestId('create-memory-dialog')).toBeInTheDocument()
    })

    it('renders all navigation links with correct href attributes', () => {
      render(<Navbar />)
      
      const dashboardLink = screen.getByText('Dashboard').closest('a')
      const memoriesLink = screen.getByText('Memories').closest('a')
      const appsLink = screen.getByText('Apps').closest('a')
      const settingsLink = screen.getByText('Settings').closest('a')
      
      expect(dashboardLink).toHaveAttribute('href', '/')
      expect(memoriesLink).toHaveAttribute('href', '/memories')
      expect(appsLink).toHaveAttribute('href', '/apps')
      expect(settingsLink).toHaveAttribute('href', '/settings')
    })
  })

  describe('Active Link Highlighting', () => {
    it('highlights the Dashboard link when on the home page', () => {
      mockPathname.mockReturnValue('/')
      render(<Navbar />)
      
      const dashboardButton = screen.getByText('Dashboard').closest('button')
      expect(dashboardButton).toHaveClass('bg-zinc-800', 'text-white')
    })

    it('highlights the Memories link when on the memories page', () => {
      mockPathname.mockReturnValue('/memories')
      render(<Navbar />)
      
      const memoriesButton = screen.getByText('Memories').closest('button')
      expect(memoriesButton).toHaveClass('bg-zinc-800', 'text-white')
    })

    it('highlights the Apps link when on the apps page', () => {
      mockPathname.mockReturnValue('/apps')
      render(<Navbar />)
      
      const appsButton = screen.getByText('Apps').closest('button')
      expect(appsButton).toHaveClass('bg-zinc-800', 'text-white')
    })

    it('highlights the Settings link when on the settings page', () => {
      mockPathname.mockReturnValue('/settings')
      render(<Navbar />)
      
      const settingsButton = screen.getByText('Settings').closest('button')
      expect(settingsButton).toHaveClass('bg-zinc-800', 'text-white')
    })

    it('does not highlight inactive links', () => {
      mockPathname.mockReturnValue('/memories')
      render(<Navbar />)
      
      const dashboardButton = screen.getByText('Dashboard').closest('button')
      const appsButton = screen.getByText('Apps').closest('button')
      
      expect(dashboardButton).toHaveClass('text-zinc-300')
      expect(appsButton).toHaveClass('text-zinc-300')
    })
  })

  describe('Refresh Functionality', () => {
    it('calls appropriate fetchers when refresh button is clicked from home page', async () => {
      const mockFetchStats = jest.fn()
      const mockFetchMemories = jest.fn()
      
      // Mock the hooks with specific implementations
      jest.doMock('@/hooks/useStats', () => ({
        useStats: () => ({
          fetchStats: mockFetchStats,
        }),
      }))
      
      jest.doMock('@/hooks/useMemoriesApi', () => ({
        useMemoriesApi: () => ({
          fetchMemories: mockFetchMemories,
          fetchMemoryById: jest.fn(),
          fetchAccessLogs: jest.fn(),
          fetchRelatedMemories: jest.fn(),
        }),
      }))
      
      mockPathname.mockReturnValue('/')
      render(<Navbar />)
      
      const refreshButton = screen.getByText('Refresh')
      fireEvent.click(refreshButton)
      
      await waitFor(() => {
        expect(mockFetchStats).toHaveBeenCalled()
        expect(mockFetchMemories).toHaveBeenCalled()
      })
    })

    it('renders refresh button with correct styling', () => {
      render(<Navbar />)
      
      const refreshButton = screen.getByText('Refresh').closest('button')
      expect(refreshButton).toHaveClass('border-zinc-700/50', 'bg-zinc-900', 'hover:bg-zinc-800')
    })
  })

  describe('Logo Link', () => {
    it('renders logo link that navigates to home page', () => {
      render(<Navbar />)
      
      const logoLink = screen.getByAltText('OpenMemory').closest('a')
      expect(logoLink).toHaveAttribute('href', '/')
    })

    it('renders logo image with correct attributes', () => {
      render(<Navbar />)
      
      const logoImage = screen.getByAltText('OpenMemory')
      expect(logoImage).toHaveAttribute('src', '/logo.svg')
      expect(logoImage).toHaveAttribute('width', '26')
      expect(logoImage).toHaveAttribute('height', '26')
    })
  })

  describe('Responsive Design', () => {
    it('renders with correct responsive classes', () => {
      render(<Navbar />)
      
      const header = screen.getByRole('banner')
      expect(header).toHaveClass('sticky', 'top-0', 'z-50', 'w-full')
      
      const container = header.querySelector('.container')
      expect(container).toHaveClass('flex', 'h-14', 'items-center', 'justify-between')
    })
  })

  describe('Accessibility', () => {
    it('has proper semantic structure', () => {
      render(<Navbar />)
      
      const header = screen.getByRole('banner')
      expect(header).toBeInTheDocument()
      
      const navigation = screen.getByRole('navigation', { hidden: true })
      expect(navigation).toBeInTheDocument()
    })

    it('has accessible button elements', () => {
      render(<Navbar />)
      
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(0)
      
      buttons.forEach(button => {
        expect(button).toBeInTheDocument()
      })
    })
  })
}) 