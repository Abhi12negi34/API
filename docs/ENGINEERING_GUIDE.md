# 📐 Engineering Deep Dive: Absolute-Confidence 400+ Engine

This document provides technical architectural details for the **AI API Testing Agent** for engineers expanding or integrating the suite.

---

## 🏛️ Comprehensive Architecture

The agent is designed as a **Specialized Expert System** rather than a general LLM. It combines high-level reasoning (LLM-based Strategy) with low-level deterministic execution (Industrial Tools).

### 1. Strategy Layer (CrewAI)
We utilize a multi-agent orchestration for the planning phase:
-   **Task 1 (Discovery)**: Uses the `keploy_intercept_proxy` to capture real-world traffic patterns and map the shadow API surface.
-   **Task 2 (Strategy)**: Analyzes the discovery baseline to prioritize specific sensors from the 400+ tool repository based on the detected tech stack (e.g., if GraphQL is detected, prioritize GraphQL DoS sensors).

### 2. Execution Layer (api_execution_agent)
The execution agent follows a **Scenario-Based Tool Execution Architecture**. Each scenario emitted by the strategy agent is mapped to supported tool functions and normalized into a report-friendly results tree.

#### Key Sensor Logics:
-   **Security**: Uses OWASP ZAP (DAST) for baseline scanning and custom logic for **Blind timing attacks**, **JWT hijacking**, and **IDOR detection**.
-   **Performance**: Wraps **k6** scenarios and performs custom **CPU hot-path profiling** via OS-level instruction monitoring.
-   **Efficiency**: Measures kernel-level **SoftIRQ frequency** and **memory page-fault rates** to detect invisible performance overhead.

### 3. Absolute Path-Traceability
To ensure findings are actionable, every sensor result is injected with its targeted URL:
```python
# Internal Logic
target_url = "https://example.com"
path = f"{target_url}/api/v1/user" # Guaranteed Absolute URL
```

---

## ⚙️ Configuration Schema

The behavior of the agent is controlled via `config/config.yaml`:

| Field | Description | default |
| :--- | :--- | :--- |
| `weights` | Multiplier for each USER PASS attribute score. | 1.0 each |
| `scans` | Configuration for ZAP/Keploy recording modes. | - |
| `reporting` | Toggle for PDF/Excel/JSON generation. | true |

---

## 🛠️ Extension Guide: Adding Your Own Sensor

To expand the certification coverage (e.g., to reach 500 sensors), follow these steps:

1.  **Identify the USER PASS category** (Usability, Security, etc.).
2.  **Add a mapping in `agents/api_execution_agent.py`** for the tool name.
3.  **Define Success Criteria**:
```python
"custom_sensor_name": {
    "success": your_boolean_logic,
    "log": "Diagnostic message for report.",
    "recommendation": "Step to fix the issue.",
    "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
    "path": f"{target_url}/target/endpoint"
}
```

---

## 📊 Reporting Logic

### Multi-Format Synchronization:
1.  **JSON**: Directly derived from the raw results dictionary for CI/CD integration.
2.  **Excel**: Uses `pandas` to flatten the attributes into a developer-scannable inventory.
3.  **PDF**: Employs a custom character-normalization layer (`latin-1 replace`) to ensure high-fidelity rendering across 400+ tool diagnostic messages.

### Scoring Logic:
$$ Attribute Score = \frac{\sum (Tool Success \times Severity Weight)}{Total Tools} \times 100 $$
- **CRITICAL/HIGH failures** act as "Blockers" even if scores are high, capping the certification tier.

---
*End of Engineering Guide*
