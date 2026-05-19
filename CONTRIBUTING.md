# Contributing to MCP Agent Platform

Thank you for your interest in contributing to the **MCP Agent Platform**!  
This project aims to be a stable, well-architected foundation for autonomous AI agents.

We welcome bug reports, feature requests, documentation improvements, and code contributions.

---

## How to Contribute

### 1. Reporting Issues
- Use the [Issues](https://github.com/k41-dev/mcp-server/issues) tab.
- Provide as much detail as possible (steps to reproduce, logs, environment).
- Use the appropriate issue template if available.

### 2. Suggesting Features
- Open a new issue with the label `enhancement`.
- Describe the use case and why it would be valuable.

### 3. Code Contributions

#### Prerequisites
- Docker + Docker Compose
- Python 3.12+
- Git

#### Local Setup
```bash
git clone https://github.com/k41-dev/mcp-server.git
cd mcp-server
cp env.example.txt .env
# Edit .env with your keys
docker compose up --build -d