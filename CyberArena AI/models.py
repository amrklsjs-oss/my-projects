from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class AgentStep:
    phase: str
    source: str
    target: str
    detail: str
    pressure: int


@dataclass
class Scenario:
    name: str
    summary: str
    nodes: List[str]
    edges: List[Tuple[str, str]]
    red_steps: List[AgentStep]
    blue_steps: List[AgentStep]


@dataclass
class SimulationState:
    turn: int = 0
    risk_score: int = 34
    red_progress: int = 0
    blue_containment: int = 0
    detected_at: str = "--"
    compromised: List[str] = field(default_factory=list)
    protected: List[str] = field(default_factory=list)
    events: List[Dict[str, str]] = field(default_factory=list)
    alerts: List[Dict[str, str]] = field(default_factory=list)


def get_scenarios() -> Dict[str, Scenario]:
    return {
        "Public Web Breach": Scenario(
            name="Public Web Breach",
            summary="AI attacker probes exposed services, steals credentials, and attempts database access.",
            nodes=["Internet", "Web Server", "VPN", "Admin Laptop", "File Server", "Database"],
            edges=[
                ("Internet", "Web Server"),
                ("Internet", "VPN"),
                ("Web Server", "Admin Laptop"),
                ("VPN", "Admin Laptop"),
                ("Admin Laptop", "Database"),
                ("Admin Laptop", "File Server"),
                ("File Server", "Database"),
            ],
            red_steps=[
                AgentStep("Recon", "Internet", "Web Server", "Port scan finds public HTTP and SSH exposure.", 12),
                AgentStep("Exploit", "Web Server", "Admin Laptop", "Outdated web framework exposes admin credentials.", 24),
                AgentStep("Lateral Movement", "Admin Laptop", "Database", "Privileged token allows attempted database access.", 32),
                AgentStep("Impact", "Database", "Database", "Attacker tries to stage customer records for exfiltration.", 38),
            ],
            blue_steps=[
                AgentStep("Detect", "Web Server", "Web Server", "Correlate scan rate with web error spikes.", 18),
                AgentStep("Contain", "Admin Laptop", "Admin Laptop", "Disable reused admin token and force password reset.", 30),
                AgentStep("Segment", "Database", "Database", "Block database access from non-approved hosts.", 40),
                AgentStep("Report", "Database", "Database", "Generate incident report with MITRE mapping.", 52),
            ],
        ),
        "Credential Theft": Scenario(
            name="Credential Theft",
            summary="AI attacker attempts account takeover through leaked credentials and VPN access.",
            nodes=["Internet", "Mail Portal", "VPN", "HR Laptop", "Identity Provider", "Payroll DB"],
            edges=[
                ("Internet", "Mail Portal"),
                ("Internet", "VPN"),
                ("Mail Portal", "HR Laptop"),
                ("VPN", "Identity Provider"),
                ("Identity Provider", "Payroll DB"),
                ("HR Laptop", "Payroll DB"),
            ],
            red_steps=[
                AgentStep("Phishing", "Internet", "Mail Portal", "Fake login lure captures a weak employee password.", 16),
                AgentStep("Login", "Internet", "VPN", "Credential stuffing succeeds without MFA.", 25),
                AgentStep("Privilege Search", "VPN", "Identity Provider", "Attacker searches for privileged group membership.", 32),
                AgentStep("Impact", "Identity Provider", "Payroll DB", "Attacker requests payroll export using stolen session.", 36),
            ],
            blue_steps=[
                AgentStep("Detect", "Mail Portal", "Mail Portal", "Detect impossible login and repeated password failures.", 20),
                AgentStep("Contain", "VPN", "VPN", "Revoke session and challenge user with MFA.", 28),
                AgentStep("Hunt", "Identity Provider", "Identity Provider", "Search for suspicious tokens and group lookups.", 40),
                AgentStep("Report", "Payroll DB", "Payroll DB", "Create account takeover incident summary.", 50),
            ],
        ),
    }


def new_state(defenses: Dict[str, bool] | None = None) -> SimulationState:
    defenses = defenses or {}
    base_risk = 34
    if defenses.get("patch_exposed_services"):
        base_risk -= 8
    if defenses.get("enforce_mfa"):
        base_risk -= 10
    if defenses.get("network_segmentation"):
        base_risk -= 12
    return SimulationState(risk_score=max(8, base_risk))


def advance_turn(scenario: Scenario, state: SimulationState, defenses: Dict[str, bool]) -> SimulationState:
    if state.turn >= 8:
        return state

    state.turn += 1
    if state.turn % 2 == 1:
        step_index = min((state.turn - 1) // 2, len(scenario.red_steps) - 1)
        step = scenario.red_steps[step_index]
        if step.target not in state.compromised:
            state.compromised.append(step.target)
        state.red_progress = min(100, step_index * 24 + 18)
        state.events.insert(0, {"team": "Red Team AI", "phase": step.phase, "detail": step.detail})
        if step.phase in {"Exploit", "Privilege Search", "Lateral Movement", "Impact"}:
            state.alerts.insert(0, {"severity": "High", "title": step.phase, "detail": step.detail})
    else:
        step_index = min((state.turn - 2) // 2, len(scenario.blue_steps) - 1)
        step = scenario.blue_steps[step_index]
        if step.target not in state.protected:
            state.protected.append(step.target)
        state.blue_containment = min(100, step_index * 23 + 20)
        state.detected_at = state.detected_at if state.detected_at != "--" else f"Turn {state.turn}"
        state.events.insert(0, {"team": "Blue Team AI", "phase": step.phase, "detail": step.detail})
        state.alerts.insert(0, {"severity": "Response", "title": step.phase, "detail": step.detail})

    state.risk_score = calculate_risk(state, defenses)
    return state


def calculate_risk(state: SimulationState, defenses: Dict[str, bool]) -> int:
    defense_bonus = 0
    defense_bonus += 8 if defenses.get("patch_exposed_services") else 0
    defense_bonus += 10 if defenses.get("enforce_mfa") else 0
    defense_bonus += 12 if defenses.get("network_segmentation") else 0

    attack_pressure = len(state.compromised) * 12 + state.red_progress * 0.28
    containment = len(state.protected) * 9 + state.blue_containment * 0.22
    score = 34 + attack_pressure - containment - defense_bonus
    return max(6, min(99, round(score)))


def generate_incident_report(scenario: Scenario, state: SimulationState, defenses: Dict[str, bool]) -> str:
    status = "Contained"
    if state.risk_score >= 70:
        status = "High residual risk"
    elif state.risk_score >= 40:
        status = "Moderate residual risk"

    timeline = "\n".join(
        f"- {event['team']} / {event['phase']}: {event['detail']}"
        for event in reversed(state.events[:6])
    ) or "- No events generated yet."

    recommendations = [
        "Patch exposed services." if not defenses.get("patch_exposed_services") else "Maintain patch management for exposed services.",
        "Enforce MFA for privileged and remote access." if not defenses.get("enforce_mfa") else "Continue enforcing MFA.",
        "Segment crown-jewel systems from workstations." if not defenses.get("network_segmentation") else "Keep segmentation rules monitored.",
        "Map detections to MITRE ATT&CK techniques.",
    ]

    return f"""CyberArena AI Incident Report

Scenario: {scenario.name}
Status: {status}
Enterprise Risk Score: {state.risk_score}/100
Red Team Progress: {state.red_progress}%
Blue Team Containment: {state.blue_containment}%
Detection Time: {state.detected_at}

Executive Summary:
{scenario.summary}

Key Timeline:
{timeline}

Recommended Actions:
- {chr(10).join(recommendations)}

MITRE ATT&CK Mapping:
- Reconnaissance
- Initial Access
- Credential Access
- Lateral Movement
- Collection
- Exfiltration or Impact
"""
