 # AI-Powered API Testing Agent: Active Resilience Engine

An autonomous, 360-degree quality certification authority designed for enterprise API ecosystems. Built on the **USER PASS** framework and extended with the **Active Resilience Engine**, this agent combines discovery, OpenAPI coverage boosting, mock chaos, PII auditing, and behavioral drift certification.

---

## 🎯 Core Purpose
The Absolute-Confidence Suite exists to eliminate the "Quality Gap" in modern API development. It moves beyond simple functional testing into deep-tier industrial auditing across eight critical dimensions, providing a mathematical "Certification Tier" (Platinum, Gold, Silver, Bronze) for every deployment.

## 🏛️ Project Architecture
The agent operates a deterministic 3-Phase Lifecycle using **CrewAI** for strategy and execution:

1.  **Phase 1: Discovery & Strategy (CrewAI)**
    *   **ApiDiscoveryAgent**: Maps the API surface, identifying hidden shadow endpoints and undocumented parameters via service-mesh interception.
    *   **ApiStrategyAgent**: Orchestrates the 400+ tool suite into a target-specific audit plan.
2.  **Phase 2: Industrial Execution (api_execution_agent)**
    *   **Deterministic Tool Executor**: Runs the assigned scenario tools and returns normalized results for analysis and certification.
    *   **Absolute Path-Traceability**: Every finding is explicitly linked to an absolute diagnostic URL or artifact path.
3.  **Phase 3: Analysis & Certification (Scorer & Reports)**
    *   **CertificationScorer**: Weights findings to compute a global quality score.
    *   **Multi-Format Reporting**: Generates definitive industrial-grade Excel, PDF, and JSON reports.

## ⚡ Quick Start Guide

### 1. Prerequisites
*   Python 3.10+
*   Docker (for Keploy and ZAP instances)
*   k6 binary installed in path

### 2. Configuration
Define your quality weights in `config/`:
```yaml
# config/config.yaml
weights:
  security: 0.25
  performance: 0.15
  reliability: 0.20
  # ...
```

### 3. Execution
Run a full 400-sensor audit against any target URL:
```bash
python main.py https://api.your-system.com/
```

The engine will create local `keploy/` artifacts for discovery, generated traces, chaos-mutated mocks, and drift comparison reports when available.

## 📊 Sample Output: USER PASS Dashboard
```text
========================================================================
  Attribute         Score   Weight      Tools  Blockers   Verdict
------------------------------------------------------------------------
  USABILITY        100.0%      10%       15/15         0      PASS
  SECURITY          82.4%      25%       45/52         3      FAIL
  EFFICIENCY        95.1%      15%       32/34         0      PASS
  ...
------------------------------------------------------------------------
  FINAL SCORE : 88.45 / 100 | TIER : [GOLD]
  TOTAL BLOCKERS : 3 (CRITICAL/HIGH issues detected)
========================================================================
```

## 🛠️ USER PASS Framework Coverage
*   **U - Usability**: UI Jank (60fps), Mental Model Consistency, Input Masking Accuracy.
*   **S - Stability**: Kernel Panic Resilience, Background Worker Drift, FD Exhaustion Recovery.
*   **E - Efficiency**: SSR TTI Overhead, SoftIRQ Handling, TCP Congestion (BBR) Efficiency.
*   **R - Reliability**: Raft Leader Convergence Speed, Quorum Persistence Lag, MTTR Recovery.
*   **P - Performance**: P99.99 Async Event-Loop Lag, Hot-Mutex Profiling, L1/L2 Cache Pressure.
*   **A - Accessibility**: WCAG AAA Spacing, Aria-Flowto Reading Order, Contrast Focus-Rings.
*   **S - Scalability**: Shard Rebalancing Overhead, Redis Slot Fairness, Autoscale Thrashing.
*   **S - Security**: Blind Timing SQLi, JWT 'jku' Hijacking, SVG XSS, Prototype Pollution.

---
*For a deep dive into the underlying engineering logic and tool-level implementation, refer to the [Engineering Guide](docs/ENGINEERING_GUIDE.md).*
