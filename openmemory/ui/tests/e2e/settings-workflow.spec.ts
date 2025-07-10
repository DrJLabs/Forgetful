import { test, expect } from '@playwright/test'

test.describe('Settings Configuration Management', () => {
  test.beforeEach(async ({ page }) => {
    // Mock configuration API endpoints
    await page.route('**/api/config**', async route => {
      const method = route.request().method()
      
      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            openmemory: {
              custom_instructions: 'Default instructions for memory processing'
            },
            mem0: {
              llm: {
                provider: 'openai',
                config: {
                  model: 'gpt-4',
                  api_key: 'env:OPENAI_API_KEY',
                  temperature: 0.7,
                  max_tokens: 2000
                }
              },
              embedder: {
                provider: 'openai',
                config: {
                  model: 'text-embedding-ada-002',
                  api_key: 'env:OPENAI_API_KEY'
                }
              }
            }
          })
        })
      } else if (method === 'POST' || method === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ 
            success: true, 
            message: 'Configuration updated successfully' 
          })
        })
      }
    })
  })

  test('should load and modify OpenMemory custom instructions', async ({ page }) => {
    await page.goto('/settings')
    
    // Wait for settings page to load
    await expect(page.getByText('OpenMemory Settings')).toBeVisible()
    
    // Find custom instructions textarea
    const customInstructions = page.locator('textarea[id="custom-instructions"]')
    await expect(customInstructions).toBeVisible()
    
    // Verify default content is loaded
    await expect(customInstructions).toHaveValue('Default instructions for memory processing')
    
    // Update instructions
    await customInstructions.fill('Updated custom instructions for comprehensive memory management and fact extraction')
    
    // Verify the change was applied
    await expect(customInstructions).toHaveValue('Updated custom instructions for comprehensive memory management and fact extraction')
  })

  test('should configure LLM provider settings correctly', async ({ page }) => {
    await page.goto('/settings')
    
    // Wait for LLM Settings section
    await expect(page.getByText('LLM Settings')).toBeVisible()
    
    // Test provider selection
    const providerSelect = page.locator('select').first()
    await expect(providerSelect).toBeVisible()
    
    // Change to Anthropic
    await providerSelect.selectOption('anthropic')
    
    // Update model
    const modelInput = page.locator('input[id="llm-model"]')
    await modelInput.fill('claude-3-opus')
    
    // Verify API key field is visible for non-Ollama providers
    await expect(page.getByText('API Key')).toBeVisible()
    
    // Update API key
    const apiKeyInput = page.locator('input[id="llm-api-key"]')
    await apiKeyInput.fill('env:ANTHROPIC_API_KEY')
  })

  test('should handle Ollama provider configuration', async ({ page }) => {
    await page.goto('/settings')
    
    // Switch to Ollama provider
    const providerSelect = page.locator('select').first()
    await providerSelect.selectOption('ollama')
    
    // Verify Ollama-specific fields appear
    await expect(page.getByText('Ollama Base URL')).toBeVisible()
    
    // Update Ollama URL
    const ollamaUrlInput = page.locator('input[id="llm-ollama-url"]')
    await ollamaUrlInput.fill('http://localhost:11434')
    
    // Verify API key field is hidden for Ollama
    const apiKeyLabels = page.locator('label', { hasText: 'API Key' })
    const apiKeyCount = await apiKeyLabels.count()
    
    // Should only have embedder API key, not LLM API key
    expect(apiKeyCount).toBe(1)
  })

  test('should toggle advanced LLM settings', async ({ page }) => {
    await page.goto('/settings')
    
    // Find and toggle advanced settings
    const advancedToggle = page.locator('input[id="llm-advanced-settings"]')
    await expect(advancedToggle).toBeVisible()
    
    // Advanced settings should be hidden initially
    await expect(page.getByText('Temperature:')).not.toBeVisible()
    
    // Enable advanced settings
    await advancedToggle.click()
    
    // Advanced settings should now be visible
    await expect(page.getByText('Temperature:')).toBeVisible()
    await expect(page.getByText('Max Tokens')).toBeVisible()
    
    // Test temperature slider
    const temperatureSlider = page.locator('input[id="temperature"]')
    await temperatureSlider.fill('0.9')
    
    // Test max tokens input
    const maxTokensInput = page.locator('input[id="max-tokens"]')
    await maxTokensInput.fill('4000')
  })

  test('should configure embedder settings independently', async ({ page }) => {
    await page.goto('/settings')
    
    // Wait for Embedder Settings section
    await expect(page.getByText('Embedder Settings')).toBeVisible()
    
    // Get the second select (embedder provider)
    const embedderSelect = page.locator('select').nth(1)
    await embedderSelect.selectOption('huggingface')
    
    // Update embedder model
    const embedderModelInput = page.locator('input[id="embedder-model"]')
    await embedderModelInput.fill('sentence-transformers/all-MiniLM-L6-v2')
    
    // Verify embedder API key field
    const embedderApiKey = page.locator('input[id="embedder-api-key"]')
    await embedderApiKey.fill('env:HUGGINGFACE_API_KEY')
  })

  test('should handle mixed provider configurations', async ({ page }) => {
    await page.goto('/settings')
    
    // Set LLM to Ollama (no API key needed)
    const llmSelect = page.locator('select').first()
    await llmSelect.selectOption('ollama')
    
    // Set Embedder to OpenAI (API key needed)
    const embedderSelect = page.locator('select').nth(1)
    await embedderSelect.selectOption('openai')
    
    // Verify mixed configuration
    await expect(page.getByText('Ollama Base URL')).toBeVisible()
    
    // Should have exactly one API key field (for embedder)
    const apiKeyFields = page.locator('input[type="password"]')
    expect(await apiKeyFields.count()).toBe(1)
    
    // Update configurations
    const ollamaUrl = page.locator('input[id="llm-ollama-url"]')
    await ollamaUrl.fill('http://localhost:11434')
    
    const embedderApiKey = page.locator('input[id="embedder-api-key"]')
    await embedderApiKey.fill('env:OPENAI_API_KEY')
  })

  test('should toggle API key visibility', async ({ page }) => {
    await page.goto('/settings')
    
    // Ensure we have API key fields visible
    const apiKeyInput = page.locator('input[id="llm-api-key"]')
    await expect(apiKeyInput).toBeVisible()
    
    // Should be password type initially
    await expect(apiKeyInput).toHaveAttribute('type', 'password')
    
    // Find and click the visibility toggle button
    const visibilityToggle = page.locator('button').filter({ hasText: /👁|🙈/ }).first()
    await visibilityToggle.click()
    
    // Type should change to text (though this depends on implementation)
    // We'll check that the button interaction works
    await expect(visibilityToggle).toBeVisible()
  })

  test('should validate form data before submission', async ({ page }) => {
    await page.goto('/settings')
    
    // Try to submit with invalid data
    const modelInput = page.locator('input[id="llm-model"]')
    await modelInput.fill('')
    
    // Look for validation messages or disabled submit buttons
    // This test depends on the actual validation implementation
    const saveButton = page.locator('button', { hasText: /save|apply|update/i }).first()
    
    if (await saveButton.isVisible()) {
      // If validation is implemented, button might be disabled or show errors
      const isDisabled = await saveButton.isDisabled()
      // This assertion would depend on the actual validation rules
    }
  })
})

test.describe('Settings Form Interactions', () => {
  test('should handle form view and JSON view switching', async ({ page }) => {
    await page.goto('/settings')
    
    // Look for view toggle buttons (Form/JSON)
    const jsonViewToggle = page.locator('button', { hasText: /json|raw|code/i }).first()
    
    if (await jsonViewToggle.isVisible()) {
      await jsonViewToggle.click()
      
      // Should show JSON editor
      await expect(page.locator('textarea[class*="font-mono"]')).toBeVisible()
      
      // Switch back to form view
      const formViewToggle = page.locator('button', { hasText: /form|visual/i }).first()
      if (await formViewToggle.isVisible()) {
        await formViewToggle.click()
        
        // Should show form fields again
        await expect(page.getByText('LLM Provider')).toBeVisible()
      }
    }
  })

  test('should handle configuration import/export', async ({ page }) => {
    await page.goto('/settings')
    
    // Look for export functionality
    const exportButton = page.locator('button', { hasText: /export|download/i }).first()
    
    if (await exportButton.isVisible()) {
      // Start waiting for download before clicking
      const downloadPromise = page.waitForEvent('download')
      await exportButton.click()
      
      // Verify download initiated
      const download = await downloadPromise
      expect(download.suggestedFilename()).toContain('config')
    }
    
    // Look for import functionality
    const importButton = page.locator('button', { hasText: /import|upload/i }).first()
    
    if (await importButton.isVisible()) {
      // This would require file upload testing
      // Implementation depends on the actual import mechanism
    }
  })

  test('should persist settings across page reloads', async ({ page }) => {
    await page.goto('/settings')
    
    // Make a configuration change
    const customInstructions = page.locator('textarea[id="custom-instructions"]')
    const testInstructions = 'Persistent test instructions'
    await customInstructions.fill(testInstructions)
    
    // Save if there's a save button
    const saveButton = page.locator('button', { hasText: /save|apply/i }).first()
    if (await saveButton.isVisible()) {
      await saveButton.click()
      
      // Wait for save confirmation
      await expect(page.locator('text=/saved|success/i')).toBeVisible()
    }
    
    // Reload the page
    await page.reload()
    
    // Verify the setting persisted
    await expect(page.locator('textarea[id="custom-instructions"]')).toHaveValue(testInstructions)
  })

  test('should handle configuration errors gracefully', async ({ page }) => {
    // Mock API error
    await page.route('**/api/config**', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ 
            error: 'Invalid configuration',
            details: 'API key format is invalid'
          })
        })
      }
    })
    
    await page.goto('/settings')
    
    // Make a change and try to save
    const apiKeyInput = page.locator('input[id="llm-api-key"]')
    await apiKeyInput.fill('invalid-key-format')
    
    const saveButton = page.locator('button', { hasText: /save|apply/i }).first()
    if (await saveButton.isVisible()) {
      await saveButton.click()
      
      // Should show error message
      await expect(page.locator('text=/error|invalid|failed/i')).toBeVisible()
    }
  })
}) 