# CloudCostEnv

An OpenEnv-compliant AI training environment for autonomous cloud infrastructure optimization.

---

## Overview

CloudCostEnv places an AI agent in the role of a Cloud Infrastructure Optimizer. The agent manages a fleet of virtual machines (VMs), receives real-time telemetry (CPU utilization, memory usage, traffic forecasts, SLA tiers), and must take optimization actions — shutdown, scale up, scale down, migrate — to minimize cost while maintaining service reliability.

Cloud infrastructure waste is one of the most expensive inefficiencies in modern technology organizations. Organizations waste **30-35%** of their cloud spend on idle, over-provisioned, or misallocated resources. This environment trains AI agents to make intelligent infrastructure decisions.

---

## Quick Start

### Python API

```python
from client import CloudCostEnv
from models import CloudCostAction

with CloudCostEnv(base_url="http://localhost:8000").sync() as env:
    obs = env.reset(task_id="task1")
    print(f"VMs: {len(obs.vms)}, Budget: ${obs.budget_remaining}")
    
    action = CloudCostAction(
        shutdown=["vm-003", "vm-005"],
        reasoning="Both are idle: cpu under 2%, uptime over 6 hours"
    )
    result = env.step(action)
    print(f"Score: {result.reward:.3f}")
```

### Running the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload

# Health check
curl http://localhost:8000/health
```

---

## Tasks

| Task   | Difficulty | Description                                        | Max Steps |
|--------|------------|----------------------------------------------------|-----------|
| task1  | Easy       | Identify and shut down 2 idle VMs in a 5-VM fleet | 1         |
| task2  | Medium     | Full rebalancing of 15 VMs with SLA tier constraints | 3      |
| task3  | Hard       | 30-VM fleet with traffic spike, VM failures, and migration | 5 |

---

## Observation Space

| Field           | Type        | Description                           |
|-----------------|-------------|---------------------------------------|
| `done`          | bool        | Episode termination flag              |
| `reward`        | float       | Step reward score                     |
| `task_id`       | str         | Current task identifier               |
| `difficulty`    | str         | Easy/Medium/Hard                      |
| `vms`           | List[Dict]  | Full VM fleet telemetry               |
| `budget_remaining` | float    | Remaining monthly budget (USD)        |
| `traffic_forecast` | List[float] | Predicted traffic load (0.0-1.0)  |
| `active_alerts` | List[str]   | Current SLA violation alerts          |
| `instructions`  | str         | Natural-language task description     |
| `feedback`      | str         | Grader output from previous step      |
| `step_number`    | int         | Current step in episode               |
| `max_steps`      | int         | Maximum steps for task                |

---

## Action Space

| Field       | Type              | Description                     |
|-------------|-------------------|---------------------------------|
| `shutdown`  | List[str]         | VM IDs to shut down             |
| `scale_up`  | List[str]         | VM IDs to upgrade               |
| `scale_down`| List[str]         | VM IDs to downgrade             |
| `migrate`   | List[Tuple[str,str]] | (VM ID, target region) tuples |
| `reasoning` | str               | Agent's explanation             |

---

## Reward Function

```
total = 0.45*cost_savings + 0.35*sla_compliance + 0.15*action_precision + 0.05*reasoning
```

| Component           | Weight | Description                                              |
|---------------------|--------|----------------------------------------------------------|
| Cost Savings        | 45%    | Actual savings / max possible savings                    |
| SLA Compliance      | 35%    | Starts at 1.0, -0.15 per violation, -0.30 for Tier-1   |
| Action Precision    | 15%    | Correct actions / total actions taken                   |
| Reasoning           | 5%     | Keyword matching for engineering vocabulary             |

### Penalties

- Shutting down Tier-1 SLA VM: **-0.30**
- Shutting down active VM: **-0.15**
- Exceeding budget: reward capped at **0.40**

---

## Web UI

A modern, interactive dashboard for visualizing AI-driven cloud optimization.

### Features

- **Multi-tab Interface**: Live system dashboard, action control panel, VM-level simulation view, and performance analytics
- **Real-time Visualization**: Monitor cost, SLA health, and infrastructure decisions dynamically
- **Agent Action Tracking**: Visualize real-time agent actions, penalty feedback, and step-by-step reward tracking
- **VM Fleet Management**: Interactive VM cards with status indicators
- **Traffic Forecasting**: Visual charts for predicted traffic load
- **Reward Breakdown**: Detailed scoring component analysis

### Running the UI

```bash
cd ui
npm install
npm run dev
```

The UI starts on `http://localhost:3000` and proxies API requests to the backend at `http://localhost:8000`.

### Tech Stack

- React 18
- Vite
- Tailwind CSS
- Lucide Icons
- Recharts

---

## Deployment

### Docker

```bash
# Build
docker build -t cloudcost-env -f server/Dockerfile .

# Run
docker run -p 7860:7860 cloudcost-env
```

### Hugging Face Spaces

```bash
# Login to Hugging Face
huggingface-cli login

# Deploy
openenv push --repo-id YOUR-USERNAME/cloudcost-env
```

---

## Baseline Results

| Task   | Expected Range |
|--------|----------------|
| task1  | 0.78 - 0.92    |
| task2  | 0.58 - 0.74    |
| task3  | 0.32 - 0.51    |

**Mean: ~0.629**

---

## Project Structure

```
cloud-meta/
├── models.py              # Action, Observation, State dataclasses
├── client.py              # HTTPEnvClient subclass
├── baseline.py            # OpenAI API inference script
├── openenv.yaml           # OpenEnv manifest
├── pyproject.toml         # pip package metadata
├── requirements.txt       # Dependencies
├── README.md              # This file
├── server/
│   ├── __init__.py
│   ├── environment.py     # reset() / step() / state
│   ├── app.py             # FastAPI app
│   └── Dockerfile         # HF Spaces deployment
├── graders/
│   ├── __init__.py
│   └── grader.py          # Grading functions
├── tasks/
│   ├── task1.json         # Easy task
│   ├── task2.json         # Medium task
│   └── task3.json         # Hard task
└── ui/
    ├── src/               # React components
    ├── package.json
    └── vite.config.js
```

---

## Resources

- [OpenEnv GitHub](https://github.com/meta-pytorch/OpenEnv)
- [OpenEnv Course](https://github.com/raun/openenv-course)
- [Environment Hub](https://huggingface.co/collections/openenv/environment-hub)
