# Mem0 Stack

<p align="center">
  <a href="https://github.com/mem0ai/mem0">
    <img src="mem0/docs/images/banner-sm.png" width="800px" alt="Mem0 Stack - Complete Memory Intelligence Platform">
  </a>
</p>

<p align="center">
  <a href="https://mem0.ai">Learn more</a>
  ·
  <a href="https://mem0.dev/DiG">Join Discord</a>
  ·
  <a href="https://mem0.dev/demo">Demo</a>
  ·
  <a href="https://mem0.dev/openmemory">OpenMemory</a>
</p>

<p align="center">
  <a href="https://mem0.dev/DiG">
    <img src="https://dcbadge.vercel.app/api/server/6PzXDgEjG5?style=flat" alt="Mem0 Discord">
  </a>
  <a href="https://pepy.tech/project/mem0ai">
    <img src="https://img.shields.io/pypi/dm/mem0ai" alt="Mem0 PyPI - Downloads">
  </a>
  <a href="https://github.com/mem0ai/mem0">
    <img src="https://img.shields.io/github/commit-activity/m/mem0ai/mem0?style=flat-square" alt="GitHub commit activity">
  </a>
  <a href="https://pypi.org/project/mem0ai" target="blank">
    <img src="https://img.shields.io/pypi/v/mem0ai?color=%2334D058&label=pypi%20package" alt="Package version">
  </a>
  <a href="https://www.npmjs.com/package/mem0ai" target="blank">
    <img src="https://img.shields.io/npm/v/mem0ai" alt="Npm package">
  </a>
  <a href="https://www.ycombinator.com/companies/mem0">
    <img src="https://img.shields.io/badge/Y%20Combinator-S24-orange?style=flat-square" alt="Y Combinator S24">
  </a>
</p>

<p align="center">
  <a href="https://mem0.ai/research"><strong>📄 Building Production-Ready AI Agents with Scalable Long-Term Memory →</strong></a>
</p>
<p align="center">
  <strong>⚡ +26% Accuracy vs. OpenAI Memory • 🚀 91% Faster • 💰 90% Fewer Tokens</strong>
</p>

## 🔥 Research Highlights
- **+26% Accuracy** over OpenAI Memory on the LOCOMO benchmark
- **91% Faster Responses** than full-context, ensuring low-latency at scale
- **90% Lower Token Usage** than full-context, cutting costs without compromise
- [Read the full paper](https://mem0.ai/research)

# Introduction

The **Mem0 Stack** is a comprehensive memory intelligence platform that combines the power of [Mem0](https://mem0.ai) ("mem-zero") with [OpenMemory](https://mem0.dev/openmemory) to provide a complete solution for AI memory management. This stack enables personalized AI interactions with intelligent memory layers, supporting both hosted and self-hosted deployments.

## 🏗️ Architecture Overview

The Mem0 Stack consists of several key components:

- **Mem0 Core**: The intelligent memory layer that enhances AI assistants and agents
- **OpenMemory**: Your personal memory layer for LLMs - private, portable, and open-source
- **MCP Integration**: Model Context Protocol server for seamless AI tool integration
- **Web UI**: React-based interface for memory management and visualization
- **Monitoring**: Comprehensive observability with Prometheus, Grafana, and alerting

### Key Features & Use Cases

**Core Capabilities:**
- **Multi-Level Memory**: Seamlessly retains User, Session, and Agent state with adaptive personalization
- **Developer-Friendly**: Intuitive API, cross-platform SDKs, and a fully managed service option
- **Private & Portable**: Your memories live locally, giving you complete control over your data
- **MCP Integration**: Model Context Protocol support for seamless AI tool integration

**Applications:**
- **AI Assistants**: Consistent, context-rich conversations
- **Customer Support**: Recall past tickets and user history for tailored help
- **Healthcare**: Track patient preferences and history for personalized care
- **Productivity & Gaming**: Adaptive workflows and environments based on user behavior

## 🚀 Quickstart Guide

### Prerequisites
- Docker and Docker Compose
- Python 3.9+ (for backend development)
- Node.js (for frontend development)
- OpenAI API Key (required for LLM interactions)

### 1. Set Up Environment Variables

Before running the project, you need to configure environment variables:

```bash
# Copy example environment files
cp openmemory/api/.env.example openmemory/api/.env
cp openmemory/ui/.env.example openmemory/ui/.env

# Edit the files with your configuration
# openmemory/api/.env
OPENAI_API_KEY=sk-xxx
USER=<user-id> # The User Id you want to associate the memories with

# openmemory/ui/.env
NEXT_PUBLIC_API_URL=http://localhost:8765
NEXT_PUBLIC_USER_ID=<user-id> # Same as the user id for environment variable in api
```

### 2. Build and Run the Project

```bash
# Build all components
make build

# Start the entire stack
make up
```

After running these commands, you will have:
- **OpenMemory MCP server**: http://localhost:8765 (API documentation at http://localhost:8765/docs)
- **OpenMemory UI**: http://localhost:3000
- **Mem0 API**: http://localhost:8000
- **Monitoring Dashboard**: http://localhost:9090 (Grafana)

### 3. MCP Client Setup

Configure OpenMemory Local MCP to a client:

```bash
npx @openmemory/install local http://localhost:8765/mcp/<client-name>/sse/<user-id> --client <client-name>
```

Replace `<client-name>` with the desired client name and `<user-id>` with the value specified in your environment variables.

## 📦 Project Structure

```
mem0-stack/
├── mem0/                    # Mem0 core library and documentation
├── openmemory/             # OpenMemory MCP server and UI
│   ├── api/               # Backend APIs + MCP server
│   └── ui/                # Frontend React application
├── monitoring/             # Prometheus, Grafana, and alerting
├── scripts/               # Utility scripts and health checks
├── docs/                  # Project documentation
└── docker-compose.yml     # Complete stack orchestration
```

## 🔗 Integrations & Demos

- **ChatGPT with Memory**: Personalized chat powered by Mem0 ([Live Demo](https://mem0.dev/demo))
- **Browser Extension**: Store memories across ChatGPT, Perplexity, and Claude ([Chrome Extension](https://chromewebstore.google.com/detail/onihkkbipkfeijkadecaafbgagkhglop?utm_source=item-share-cb))
- **Langgraph Support**: Build a customer bot with Langgraph + Mem0 ([Guide](https://docs.mem0.ai/integrations/langgraph))
- **CrewAI Integration**: Tailor CrewAI outputs with Mem0 ([Example](https://docs.mem0.ai/integrations/crewai))

## 🛠️ Development

### Basic Usage with Mem0

Mem0 requires an LLM to function, with `gpt-4o-mini` from OpenAI as the default. However, it supports a variety of LLMs; for details, refer to our [Supported LLMs documentation](https://docs.mem0.ai/components/llms/overview).

```python
from openai import OpenAI
from mem0 import Memory

openai_client = OpenAI()
memory = Memory()

def chat_with_memories(message: str, user_id: str = "default_user") -> str:
    # Retrieve relevant memories
    relevant_memories = memory.search(query=message, user_id=user_id, limit=3)
    memories_str = "\n".join(f"- {entry['memory']}" for entry in relevant_memories["results"])

    # Generate Assistant response
    system_prompt = f"You are a helpful AI. Answer the question based on query and memories.\nUser Memories:\n{memories_str}"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": message}]
    response = openai_client.chat.completions.create(model="gpt-4o-mini", messages=messages)
    assistant_response = response.choices[0].message.content

    # Create new memories from the conversation
    messages.append({"role": "assistant", "content": assistant_response})
    memory.add(messages, user_id=user_id)

    return assistant_response
```

### Installation

Install the SDK via pip:

```bash
pip install mem0ai
```

Install SDK via npm:
```bash
npm install mem0ai
```

## 📚 Documentation & Support

- **Full Mem0 docs**: https://docs.mem0.ai
- **OpenMemory docs**: https://mem0.dev/openmemory
- **Community**: [Discord](https://mem0.dev/DiG) · [Twitter](https://x.com/mem0ai)
- **Contact**: founders@mem0.ai

## 🤝 Contributing

We are a team of developers passionate about the future of AI and open-source software. With years of experience in both fields, we believe in the power of community-driven development and are excited to build tools that make AI more accessible and personalized.

We welcome all forms of contributions:
- Bug reports and feature requests
- Documentation improvements
- Code contributions
- Testing and feedback
- Community support

How to contribute:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Join us in building the future of AI memory management! Your contributions help make the Mem0 Stack better for everyone.

## 📄 Citation

We now have a paper you can cite:

```bibtex
@article{mem0,
  title={Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory},
  author={Chhikara, Prateek and Khant, Dev and Aryan, Saket and Singh, Taranjeet and Yadav, Deshraj},
  journal={arXiv preprint arXiv:2504.19413},
  year={2025}
}
```

## ⚖️ License

Apache 2.0 — see the [LICENSE](LICENSE) file for details.
