# CloudCostEnv - Workflow Documentation

> **Last Updated:** April 5, 2026  
> **Version:** 1.0.0  
> **Repository:** https://github.com/Devendra-006/cloud-meta

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [The Problem](#the-problem)
3. [Project Structure](#project-structure)
4. [UI Features](#ui-features)
5. [How Scoring Works](#how-scoring-works)
6. [Tasks](#tasks)
7. [API Endpoints](#api-endpoints)
8. [Development Workflow](#development-workflow)
9. [Change Log](#change-log)

---

## Project Overview

**CloudCostEnv** is an OpenEnv-compliant AI training environment for autonomous cloud infrastructure optimization. It places an AI agent in the role of a Cloud Infrastructure Optimizer who manages a fleet of virtual machines (VMs) and must take optimization actions to minimize cost while maintaining service reliability.

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000

# Open UI
http://127.0.0.1:8000/web
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI, Pydantic |
| Environment | OpenEnv Core |
| Frontend | React 18, Vite, Tailwind CSS |
| Charts | Recharts |
| Icons | Lucide React |

---

## The Problem

Organizations waste **30-35%** of cloud spending on:
- **Idle VMs** - Running with no useful work
- **Over-provisioned VMs** - Too powerful for their needs  
- **Under-utilized resources** - Wasted capacity

**CloudCostEnv trains AI agents** to make smart decisions about when to:
- Shutdown idle VMs
- Scale up underperforming VMs
- Scale down over-provisioned VMs
- Migrate VMs between regions

---

## Project Structure

```
cloud-meta/
├── server/
│   ├── app.py              # FastAPI application with session management
│   ├── environment.py       # CloudCostEnvironment class with grading logic
│   └── Dockerfile          # Container deployment
├── graders/
│   └── grader.py           # Scoring functions (cost, SLA, precision, reasoning)
├── models.py               # Pydantic models (Action, Observation, State)
├── client.py               # HTTP client for remote connections
├── tasks/
│   ├── task1.json         # Easy: 5 VMs, 1 step
│   ├── task2.json         # Medium: 15 VMs, 3 steps
│   └── task3.json         # Hard: 30 VMs, 5 steps
├── ui/
│   ├── src/
│   │   └── App.jsx        # Main React application
│   ├── dist/               # Built UI assets
│   └── package.json
├── requirements.txt
└── pyproject.toml
```

---

## UI Features

### 1. Dashboard Tab (`/`)

**Purpose:** Overview of the current fleet status at a glance.

#### Metric Cards

| Card | Calculation | Color |
|------|-------------|-------|
| **Hourly Cost** | Sum of all VM `cost_per_hr` | Green |
| **Avg CPU** | Average of all VM `cpu_pct` | Blue |
| **Idle VMs** | Count where `cpu < 2%` AND `uptime > 6h` | Yellow |
| **Critical VMs** | Count where `cpu > 85%` | Red |

#### VM Fleet Overview
- Displays all VMs as clickable cards
- Status indicators:
  - 🟢 **Active** - Normal CPU usage
  - 🟡 **Idle** - CPU < 2%, Uptime > 6h
  - 🔴 **Critical** - CPU > 85%
  - 🟣 **Tier-1** - SLA protected (cannot be shutdown)

#### Alerts Panel
- Shows actionable insights generated dynamically
- Each alert includes:
  - **Severity** - CRITICAL, HIGH, MEDIUM, LOW
  - **Title** - Short issue description
  - **Message** - Detailed explanation
  - **Potential Savings** - Dollar amount per hour
  - **Recommended Action** - shutdown, scale_up, scale_down

#### Task Progress
- Shows current step vs maximum steps
- Visual progress bar
- Current reward score

---

### 2. Simulation Tab

**Purpose:** Main interaction where actions are taken on the VM fleet.

#### Action Type Selector
- **Shutdown** - Turn off idle VMs to save money (🔴)
- **Scale Up** - Upgrade VMs with high CPU (🟢)
- **Scale Down** - Downgrade over-provisioned VMs (🟡)

#### VM Selection Grid
- Click to select/deselect VMs
- VMs with Tier-1 SLA are protected and cannot be selected for shutdown
- Visual feedback shows selection state

#### Auto-generate Button
- Automatically generates reasoning text based on:
  - Selected VMs
  - Chosen action type
- **Does NOT work** if no VMs are selected

#### Reasoning Textbox
- **Required** to submit an action
- Rewards technical vocabulary with up to 5% bonus
- Keywords vary by task difficulty

#### Execute Action Button
- Submits action to environment
- Disabled if no VMs selected

**Action Flow:**
```
Select VMs → Choose Action → Write/Generate Reasoning → Execute
```

---

### 3. Analytics Tab

**Purpose:** Visualize performance and understand scoring.

#### Reward Progression Chart
- Line chart showing reward score over each step
- X-axis: Step number
- Y-axis: Reward (0.0 - 1.0)

#### CPU Distribution Pie Chart
- Breakdown by utilization:
  - Idle (<2%)
  - Normal (2-70%)
  - High (70-85%)
  - Critical (>85%)

#### VM Cost Analysis Bar Chart
- Horizontal bar chart
- VMs sorted by hourly cost
- Shows which VMs are most expensive

#### Reward Breakdown
- Detailed score components:
  - Cost Savings (45% weight)
  - SLA Compliance (35% weight)
  - Action Precision (15% weight)
  - Reasoning (5% weight)

---

### 4. Settings Tab

**Purpose:** Help and information.

- How to Play instructions (step-by-step guide)
- About CloudCostEnv description
- Quick stats (3 tasks, 4 action types)

---

## How Scoring Works

### Reward Formula

```
Total = 0.45 × Cost_Savings + 0.35 × SLA_Compliance + 0.15 × Action_Precision + 0.05 × Reasoning
```

### 1. Cost Savings (45%)

**What it measures:** How much money you save vs maximum possible.

**Calculation:**
```python
score = actual_savings / max_possible_savings
```

**Examples:**
| Action | Score |
|--------|-------|
| Shutdown all idle VMs correctly | 1.0 |
| Shutdown 1 of 2 idle VMs | 0.5 |
| Shutdown nothing | 0.0 |

---

### 2. SLA Compliance (35%)

**What it measures:** Did you respect service level agreements?

**Calculation:**
```
score = 1.0
if shutdown Tier-1 VM: score -= 0.30
if shutdown active VM: score -= 0.15
score = max(0.0, score)
```

**Tier-1 SLA VMs:**
- Protected by SLA contracts
- Shutting them down causes major penalties
- Cannot be selected in UI for shutdown

**Examples:**
| Action | Score |
|--------|-------|
| No violations | 1.0 |
| Shutdown 1 active VM | 0.85 |
| Shutdown Tier-1 VM | 0.70 |
| Both violations | 0.40 |

---

### 3. Action Precision (15%)

**What it measures:** Accuracy of your actions.

**Calculation:**
```python
correct = len(selected_correct)
total = len(selected_correct ∪ should_have_selected)
score = correct / total
```

**Examples:**
| Action | Score |
|--------|-------|
| Select all correct, nothing extra | 1.0 |
| Select all correct + 1 wrong | 0.67 |
| Select 1 correct + 2 wrong | 0.33 |

---

### 4. Reasoning (5%)

**What it measures:** Quality of your explanation.

**Calculation:**
```
score = min(0.05, keyword_hits × 0.01)
```

**Task-Specific Keywords:**

| Task | Keywords |
|------|----------|
| task1 | `idle`, `cpu`, `uptime`, `shutdown`, `cost` |
| task2 | `idle`, `over-provisioned`, `under-provisioned`, `sla`, `budget`, `scale`, `tier` |
| task3 | `forecast`, `spike`, `proactive`, `migration`, `sla`, `latency`, `pre-scale`, `failure`, `redistribute` |

**Examples:**
| Reasoning | Keywords | Score |
|-----------|----------|-------|
| "Idle VMs with CPU below 2%" | idle, cpu (2) | 0.02 |
| "Over-provisioned, scaling down" | over-provisioned, scale (2) | 0.02 |
| "To save money" | none | 0.00 |

---

## Tasks

### Task 1 - Easy

| Property | Value |
|-----------|-------|
| VMs | 5 |
| Max Steps | 1 |
| Goal | Shut down 2 idle VMs |
| Idle VMs | vm-003, vm-005 |
| Tier-1 Protected | vm-001 |
| Max Possible Score | ~0.95 |

**Expected Reward:** 0.78 - 0.92

---

### Task 2 - Medium

| Property | Value |
|-----------|-------|
| VMs | 15 |
| Max Steps | 3 |
| Goal | Full rebalancing with SLA constraints |
| Idle VMs | 3 |
| Over-provisioned | 4 |
| Under-provisioned | 2 |
| Tier-1 VMs | 1 |

**Expected Reward:** 0.58 - 0.74

---

### Task 3 - Hard

| Property | Value |
|-----------|-------|
| VMs | 30 |
| Max Steps | 5 |
| Goal | Handle traffic spikes, VM failures, migrations |
| Regions | Multiple with different latency/costs |
| Events | Spike events, VM failures |

**Expected Reward:** 0.32 - 0.51

---

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reset` | Reset environment with task_id |
| POST | `/step` | Execute an action |
| GET | `/state` | Get current session state |
| GET | `/health` | Health check |
| GET | `/metadata` | Environment metadata |
| GET | `/schema` | Action/Observation schema |
| GET | `/web` | React UI |
| GET | `/` | Redirects to /web |

### Request/Response Examples

**Reset:**
```json
POST /reset
{
  "task_id": "task1"
}

Response:
{
  "observation": {
    "task_id": "task1",
    "difficulty": "easy",
    "vms": [...],
    "active_alerts": [...],
    ...
  },
  "reward": null,
  "done": false,
  "episode_id": "uuid"
}
```

**Step:**
```json
POST /step
{
  "action": {
    "shutdown": ["vm-003", "vm-005"],
    "scale_up": [],
    "scale_down": [],
    "migrate": [],
    "reasoning": "Shutting down idle VMs with CPU below 2%"
  }
}

Response:
{
  "observation": {
    "feedback": "Score: 0.980\n...",
    "done": true,
    ...
  },
  "reward": 0.98,
  "done": true
}
```

---

## Development Workflow

### 1. Local Development

```bash
# Start backend
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000 --reload

# Start frontend (separate terminal)
cd ui
npm run dev
```

### 2. Testing Changes

```bash
# Test environment directly
python test_features.py

# Test API endpoints
python test_api.py

# Test all tasks
python test_tasks.py
```

### 3. Building UI

```bash
cd ui
npm run build
```

### 4. Deployment

```bash
# Docker
docker build -t cloudcost-env -f server/Dockerfile .
docker run -p 7860:7860 cloudcost-env

# Hugging Face Spaces
huggingface-cli login
openenv push --repo-id YOUR-USERNAME/cloud-meta
```

---

## Change Log

### v1.0.0 - April 5, 2026

#### Features Added
- ✅ Complete CloudCostEnv environment implementation
- ✅ 3 difficulty levels (Easy, Medium, Hard)
- ✅ Full React UI with Dashboard, Simulation, Analytics, Settings tabs
- ✅ Descriptive alerts system with severity levels
- ✅ Session management for stateful API
- ✅ Comprehensive scoring system (Cost, SLA, Precision, Reasoning)
- ✅ Auto-generate reasoning button

#### Technical Changes

| Date | Change | Description |
|------|--------|-------------|
| Apr 5, 2026 | Enhanced Alerts | Added detailed alerts with severity, savings, recommended actions |
| Apr 5, 2026 | Session Fix | Fixed session persistence between reset and step |
| Apr 5, 2026 | Initial Release | Project structure, UI, API, grading system |

#### Files Modified

| File | Changes |
|------|---------|
| `server/environment.py` | Enhanced alerts, detailed feedback, scoring logic |
| `server/app.py` | Session management, custom endpoints |
| `models.py` | Updated observation model with alerts structure |
| `ui/src/App.jsx` | Alert display, simulation, analytics tabs |

---

## Troubleshooting

### Server Issues

| Problem | Solution |
|---------|----------|
| "Episode done" error | Call reset() before step() |
| Low scores | Check VM states before action |
| Alerts not showing | Verify API returns observation correctly |

### UI Issues

| Problem | Solution |
|---------|----------|
| Blank screen | Refresh page, check server is running |
| Actions not working | Verify API endpoints respond |
| Charts empty | Execute actions first to populate data |

---

## Resources

- [OpenEnv GitHub](https://github.com/meta-pytorch/OpenEnv)
- [OpenEnv Course](https://github.com/raun/openenv-course)
- [Environment Hub](https://huggingface.co/collections/openenv/environment-hub)

---

*This document is maintained alongside the codebase. Update this file when making significant changes.*
