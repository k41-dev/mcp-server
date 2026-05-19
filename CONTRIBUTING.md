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

Development Workflow

Create a new branch from main:Bashgit checkout -b feat/your-feature-name
Make your changes (follow the architecture rules below).
Test locally.
Commit using our git save alias or conventional commits.
Push and open a Pull Request.

Architecture Rules (important)

Backend (backend/) contains all business logic, tools, memory, and prompt handling.
Frontend (frontend/) is a "dumb" Gradio UI — never import anything from backend/.
All communication between UI and backend happens exclusively via the MCP JSON-RPC endpoint (/mcp).
New tools must have a JSON definition in backend/tools/definitions/ and an executor in backend/tools/executors/.
Skills live in prompts/skills/, Personas in prompts/personas/.

Commit Messages
We use Conventional Commits:

feat: new feature
fix: bug fix
docs: documentation only
chore: maintenance / tooling
refactor: code change that neither fixes a bug nor adds a feature


Code Style

Follow PEP 8 for Python.
Use type hints where reasonable.
Keep functions focused and small.
Add comments for complex logic.
Update README.md if you add new major features.


Pull Request Process

Ensure your branch is up to date with main.
Make sure all tests (if any) pass.
Update documentation if needed.
Open a Pull Request with a clear title and description.
Be responsive to review feedback.


Questions?
Feel free to open an issue with the label question or reach out via Discussions.
Thank you for helping make this project better! 🚀

Maintained with ❤️ by the MCP Projektleiter