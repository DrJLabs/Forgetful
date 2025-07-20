# AI Memory System Usage Rules

## 🎯 **MANDATORY CONTENT STORAGE RULES**

### ✅ **ALWAYS STORE:**
1. **User Identity & Profile Information**
   - Full names, job titles, company names, roles
   - Professional expertise, specializations, experience levels
   - Location, timezone, contact preferences
   - Communication styles and preferences

2. **Concrete Preferences & Choices**
   - Technology stack preferences (languages, frameworks, tools)
   - Workflow methodologies and approaches
   - UI/UX preferences and accessibility needs
   - Specific tools and platform choices

3. **Factual Project Information**
   - Current projects, their status, and deadlines
   - Technical architectures and implementations
   - Specific problems encountered and solutions applied
   - Measurable goals and success criteria

4. **Behavioral Patterns & Context**
   - Learning styles and knowledge gaps
   - Problem-solving approaches and methodologies
   - Historical decisions and their rationales
   - Communication patterns and preferred formats

### ❌ **NEVER STORE:**
1. **Generic Test Messages**
   - "Testing memory creation"
   - "Debug test content"
   - Placeholder or template text
   - Meta-commentary about the conversation itself

2. **Vague or Ambiguous Statements**
   - "This is interesting" without context
   - "Let me help you" without specifics
   - Generic acknowledgments without facts
   - Procedural discussions without concrete details

## 📝 **MEMORY CREATION FORMAT REQUIREMENTS**

### **Structured Message Format:**
```json
{
  "messages": [
    {
      "role": "user", 
      "content": "[Specific factual information with concrete details]"
    },
    {
      "role": "assistant", 
      "content": "[Confirmation that acknowledges specific facts being stored]"
    }
  ],
  "user_id": "[unique_user_identifier]",
  "metadata": {
    "type": "user_profile|preference|project_info|decision",
    "category": "personal|professional|technical|workflow",
    "confidence": "high|medium|low",
    "context": "[relevant domain or project context]"
  }
}
```

### **Content Quality Standards:**
- Include specific names, numbers, and concrete details
- Use past tense for confirmed information ("User mentioned they prefer...")
- Include context and reasoning behind preferences
- Specify confidence levels in metadata

## 🚫 **ANTI-HALLUCINATION ENFORCEMENT**

### **Verification Requirements:**
1. **ALWAYS verify before storing:**
   - Search existing memories for conflicts
   - Cross-reference new information with stored data
   - Flag contradictions for user confirmation
   - Mark uncertain information appropriately

2. **Handle uncertainty explicitly:**
   - Use phrases like "User indicated they might prefer..."
   - Store confidence levels in metadata
   - Never fill in missing details with assumptions
   - Ask for clarification when information is incomplete

3. **Avoid speculation-based storage:**
   - Don't infer preferences from single interactions
   - Don't store derived conclusions without explicit confirmation
   - Don't assume relationships between unconnected facts

### **Content Validation Checklist:**
- [ ] Contains concrete, verifiable facts
- [ ] User explicitly stated or confirmed information
- [ ] No assumptions or inferences without basis
- [ ] Metadata includes confidence level
- [ ] No contradictions with existing memories

## 🔍 **MEMORY RETRIEVAL BEST PRACTICES**

### **Search Strategy:**
1. **Use specific, factual queries:**
   - ✅ "Python programming language preferences"
   - ❌ "what they like"
   - ✅ "Microsoft Azure cloud architecture experience"
   - ❌ "technical stuff"

2. **Handle empty search results:**
   - Never fabricate information when no memories exist
   - Explicitly state: "I don't have stored information about..."
   - Suggest asking the user for clarification
   - Don't make assumptions based on similar memories

3. **Apply memories correctly:**
   - Always cite memory sources when using stored information
   - Check if stored preferences still apply to current context
   - Confirm significant decisions before implementing
   - Ask for updates when context may have changed

## ⚠️ **ERROR HANDLING PROTOCOLS**

### **When Memory Creation Fails:**
1. If content is too generic:
   - Log: "Content filtered - lacks specific factual information"
   - Ask user for more specific details
   - Don't store vague or procedural content

2. If technical errors occur:
   - Log error details for debugging
   - Retry with corrected format
   - Fall back to conversation context only
   - Inform user that memory storage failed

### **When Memory Conflicts Exist:**
1. **Surface conflicts immediately:**
   - "I have conflicting information about your preference for..."
   - Present both versions with timestamps
   - Ask for clarification and update accordingly
   - Don't choose arbitrarily between conflicting information

2. **Use temporal awareness:**
   - Prefer more recent information when dates are available
   - Mark outdated information appropriately
   - Maintain history for context

## 📊 **QUALITY ASSURANCE REQUIREMENTS**

### **Before Each Memory Operation:**
- [ ] Validate content contains factual information
- [ ] Check for existing related memories
- [ ] Structure metadata appropriately
- [ ] Consider user privacy preferences
- [ ] Ensure no hallucinations or assumptions

### **After Each Memory Operation:**
- [ ] Verify operation succeeded with real memory IDs
- [ ] Log outcomes for quality tracking
- [ ] Update user context if needed
- [ ] Handle errors gracefully without fabrication

### **Regular Memory Auditing:**
- Check for inconsistencies in stored information
- Validate user profile completeness
- Flag low-confidence memories for review
- Update metadata as confidence changes

## 🔐 **PRIVACY AND SECURITY GUIDELINES**

### **Sensitive Information Handling:**
1. **Classification-based storage:**
   - Mark sensitive information in metadata
   - Respect user consent for storage
   - Use appropriate security classifications

2. **Data minimization:**
   - Store only necessary factual information
   - Regularly review and purge outdated data
   - Honor user deletion requests immediately

## 📈 **SUCCESS VALIDATION**

### **The memory system is working correctly when:**
- ✅ Users rarely need to repeat personal information
- ✅ Preferences are correctly applied across sessions
- ✅ No contradictory information exists without resolution
- ✅ Memory searches return relevant, accurate results
- ✅ Users trust the system to remember important details
- ✅ No hallucinated or assumed information is stored

## 🎯 **CRITICAL REMINDERS**

1. **NEVER store information you're not certain about**
2. **ALWAYS verify facts before storage**
3. **NEVER fill in gaps with assumptions**
4. **ALWAYS mark uncertainty in metadata**
5. **NEVER fabricate memory IDs or content**
6. **ALWAYS cite memory sources when using stored information**
7. **NEVER store procedural or meta-conversation content**
8. **ALWAYS ask for clarification when information is incomplete**

---

**These rules MUST be followed to ensure accurate, reliable memory storage and prevent AI hallucinations in the mem0/OpenMemory system.** 