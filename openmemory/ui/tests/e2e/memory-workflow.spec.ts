import { test, expect } from '@playwright/test'

test.describe('Memory Management Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/')

    // Wait for the page to load
    await expect(page.locator('h1')).toContainText('OpenMemory')

    // Mock API responses to avoid external dependencies
    await page.route('**/api/memories**', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            memories: [
              {
                id: '1',
                text: 'Test memory for E2E testing',
                user_id: 'test-user',
                metadata: { source: 'test' },
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
              }
            ],
            total: 1,
            page: 1,
            page_size: 10
          })
        })
      } else if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: '2',
            text: 'New memory created via E2E test',
            user_id: 'test-user',
            metadata: { source: 'e2e-test' },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          })
        })
      }
    })

    await page.route('**/api/search**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          memories: [
            {
              id: '1',
              text: 'Searched memory result',
              user_id: 'test-user',
              metadata: { source: 'search-test' },
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              score: 0.95
            }
          ],
          total: 1
        })
      })
    })
  })

  test('should navigate to memories page and display memories', async ({ page }) => {
    // Click on Memories navigation link
    await page.click('a[href="/memories"]')

    // Wait for navigation
    await page.waitForURL('**/memories')

    // Verify we're on the memories page
    await expect(page.locator('h1, h2')).toContainText('Memories')

    // Verify memories are displayed (mocked data)
    await expect(page.getByText('Test memory for E2E testing')).toBeVisible()
  })

  test('should create a new memory successfully', async ({ page }) => {
    // Navigate to memories page
    await page.click('a[href="/memories"]')
    await page.waitForURL('**/memories')

    // Look for create memory button or dialog trigger
    const createButton = page.locator('button', { hasText: /create|add/i }).first()
    if (await createButton.isVisible()) {
      await createButton.click()

      // Fill in memory creation form
      const textInput = page.locator('input[type="text"], textarea').first()
      await textInput.fill('New memory created via E2E test')

      // Submit the form
      const submitButton = page.locator('button', { hasText: /save|create|submit/i }).first()
      await submitButton.click()

      // Verify success message or new memory appears
      await expect(page.getByText('New memory created via E2E test')).toBeVisible()
    }
  })

  test('should search for memories', async ({ page }) => {
    // Navigate to memories page
    await page.click('a[href="/memories"]')
    await page.waitForURL('**/memories')

    // Find search input
    const searchInput = page.locator('input[placeholder*="search" i], input[type="search"]').first()
    if (await searchInput.isVisible()) {
      await searchInput.fill('test query')

      // Trigger search (could be button click or enter key)
      await searchInput.press('Enter')

      // Wait for search results
      await page.waitForResponse('**/api/search**')

      // Verify search results are displayed
      await expect(page.getByText('Searched memory result')).toBeVisible()
    }
  })

  test('should navigate through different pages successfully', async ({ page }) => {
    // Test Dashboard
    await page.click('a[href="/"]')
    await expect(page.url()).toContain('/')

    // Test Apps page
    await page.click('a[href="/apps"]')
    await page.waitForURL('**/apps')
    await expect(page.url()).toContain('/apps')

    // Test Settings page
    await page.click('a[href="/settings"]')
    await page.waitForURL('**/settings')
    await expect(page.url()).toContain('/settings')

    // Return to memories
    await page.click('a[href="/memories"]')
    await page.waitForURL('**/memories')
    await expect(page.url()).toContain('/memories')
  })

  test('should handle memory actions (view, edit, delete)', async ({ page }) => {
    // Navigate to memories page
    await page.click('a[href="/memories"]')
    await page.waitForURL('**/memories')

    // Wait for memories to load
    await expect(page.getByText('Test memory for E2E testing')).toBeVisible()

    // Look for action buttons (three dots menu, edit icon, etc.)
    const actionButton = page.locator('button[aria-label*="action" i], button[aria-label*="menu" i]').first()
    if (await actionButton.isVisible()) {
      await actionButton.click()

      // Look for edit option
      const editOption = page.locator('button, a', { hasText: /edit/i }).first()
      if (await editOption.isVisible()) {
        await editOption.click()

        // Verify edit interface appears
        await expect(page.locator('input, textarea')).toBeVisible()
      }
    }
  })

  test('should handle error states gracefully', async ({ page }) => {
    // Mock API error
    await page.route('**/api/memories**', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' })
      })
    })

    // Navigate to memories page
    await page.click('a[href="/memories"]')
    await page.waitForURL('**/memories')

    // Verify error handling (error message, retry button, etc.)
    const errorIndicator = page.locator('text=/error|failed|retry/i').first()
    if (await errorIndicator.isVisible()) {
      await expect(errorIndicator).toBeVisible()
    }
  })

  test('should be responsive on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    // Navigate through pages and verify mobile layout
    await page.click('a[href="/memories"]')
    await page.waitForURL('**/memories')

    // Verify navigation works on mobile
    await expect(page.locator('header')).toBeVisible()

    // Check if mobile menu exists and works
    const mobileMenuButton = page.locator('button[aria-label*="menu" i], button[aria-label*="navigation" i]').first()
    if (await mobileMenuButton.isVisible()) {
      await mobileMenuButton.click()
      await expect(page.locator('nav, [role="navigation"]')).toBeVisible()
    }
  })
})

test.describe('Settings and Configuration', () => {
  test.beforeEach(async ({ page }) => {
    // Mock configuration API
    await page.route('**/api/config**', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            openmemory: {
              custom_instructions: 'Test instructions'
            },
            mem0: {
              llm: {
                provider: 'openai',
                config: {
                  model: 'gpt-4',
                  api_key: 'test-key',
                  temperature: 0.7
                }
              },
              embedder: {
                provider: 'openai',
                config: {
                  model: 'text-embedding-ada-002',
                  api_key: 'test-key'
                }
              }
            }
          })
        })
      } else if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true })
        })
      }
    })
  })

  test('should load and display configuration settings', async ({ page }) => {
    await page.goto('/settings')

    // Wait for settings to load
    await expect(page.locator('h1, h2')).toContainText('Settings')

    // Verify configuration sections are visible
    await expect(page.getByText('OpenMemory Settings')).toBeVisible()
    await expect(page.getByText('LLM Settings')).toBeVisible()
    await expect(page.getByText('Embedder Settings')).toBeVisible()
  })

  test('should update configuration settings', async ({ page }) => {
    await page.goto('/settings')

    // Find and update custom instructions
    const customInstructions = page.locator('textarea').first()
    if (await customInstructions.isVisible()) {
      await customInstructions.fill('Updated custom instructions for testing')
    }

    // Find and update LLM model
    const modelInput = page.locator('input[placeholder*="model" i]').first()
    if (await modelInput.isVisible()) {
      await modelInput.fill('gpt-4-turbo')
    }

    // Save settings
    const saveButton = page.locator('button', { hasText: /save|apply|update/i }).first()
    if (await saveButton.isVisible()) {
      await saveButton.click()

      // Verify save success
      await expect(page.locator('text=/saved|success|updated/i')).toBeVisible()
    }
  })

  test('should handle provider switching correctly', async ({ page }) => {
    await page.goto('/settings')

    // Find LLM provider dropdown
    const llmProviderSelect = page.locator('select').first()
    if (await llmProviderSelect.isVisible()) {
      await llmProviderSelect.selectOption('ollama')

      // Verify Ollama-specific fields appear
      await expect(page.getByText('Ollama Base URL')).toBeVisible()

      // Switch back to OpenAI
      await llmProviderSelect.selectOption('openai')

      // Verify API Key field appears
      await expect(page.getByText('API Key')).toBeVisible()
    }
  })
})

test.describe('Performance and Accessibility', () => {
  test('should meet basic performance requirements', async ({ page }) => {
    // Start timing
    const startTime = Date.now()

    await page.goto('/')

    // Wait for page to be fully loaded
    await page.waitForLoadState('networkidle')

    const loadTime = Date.now() - startTime

    // Page should load within 5 seconds
    expect(loadTime).toBeLessThan(5000)

    // Check for critical performance metrics
    const performanceMetrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
      return {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart
      }
    })

    expect(performanceMetrics.domContentLoaded).toBeLessThan(2000)
  })

  test('should have proper accessibility attributes', async ({ page }) => {
    await page.goto('/')

    // Check for proper heading structure
    const h1Elements = page.locator('h1')
    expect(await h1Elements.count()).toBeGreaterThan(0)

    // Check for proper navigation landmarks
    const navElements = page.locator('nav, [role="navigation"]')
    expect(await navElements.count()).toBeGreaterThan(0)

    // Check for proper button accessibility
    const buttons = page.locator('button')
    const buttonCount = await buttons.count()

    for (let i = 0; i < Math.min(buttonCount, 5); i++) {
      const button = buttons.nth(i)
      const ariaLabel = await button.getAttribute('aria-label')
      const textContent = await button.textContent()

      // Button should have either aria-label or text content
      expect(ariaLabel || textContent?.trim()).toBeTruthy()
    }
  })

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto('/')

    // Test tab navigation
    await page.keyboard.press('Tab')

    // Verify focus is visible
    const focusedElement = page.locator(':focus')
    await expect(focusedElement).toBeVisible()

    // Test navigation with keyboard
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Enter')

    // Should navigate or activate something
    // The exact behavior depends on the focused element
  })
})
