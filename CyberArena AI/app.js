const scenarios = {
  "web-breach": {
    summary: "AI attacker starts outside the company and probes exposed services.",
    nodes: [
      { id: "internet", label: "Internet", sub: "External", x: 92, y: 260 },
      { id: "web", label: "Web Server", sub: "CVE risk", x: 275, y: 175 },
      { id: "vpn", label: "VPN", sub: "Remote access", x: 275, y: 345 },
      { id: "admin", label: "Admin Laptop", sub: "Privileged", x: 495, y: 175 },
      { id: "files", label: "File Server", sub: "Internal docs", x: 495, y: 345 },
      { id: "db", label: "Database", sub: "Crown jewel", x: 720, y: 260, target: true }
    ],
    edges: [["internet", "web"], ["internet", "vpn"], ["web", "admin"], ["vpn", "admin"], ["admin", "db"], ["files", "db"], ["admin", "files"]],
    redSteps: [
      ["scan", "Internet", "Web Server", "Port scan finds public HTTP and SSH exposure.", 12],
      ["exploit", "Web Server", "Admin Laptop", "Outdated web framework creates a path to credentials.", 24],
      ["lateral", "Admin Laptop", "Database", "Privileged token allows attempted database access.", 32],
      ["impact", "Database", "Database", "Attacker tries to stage customer records for exfiltration.", 38]
    ],
    blueSteps: [
      ["detect", "Web Server", "Correlate scan rate with web error spikes.", 18],
      ["contain", "Admin Laptop", "Disable reused admin token and force password reset.", 30],
      ["segment", "Database", "Block database access from non-approved hosts.", 40],
      ["report", "Database", "Generate incident report with MITRE mapping.", 52]
    ]
  },
  "credential-theft": {
    summary: "AI attacker attempts account takeover through leaked credentials and VPN access.",
    nodes: [
      { id: "internet", label: "Internet", sub: "External", x: 92, y: 260 },
      { id: "mail", label: "Mail Portal", sub: "Phishing target", x: 275, y: 170 },
      { id: "vpn", label: "VPN", sub: "MFA optional", x: 275, y: 350 },
      { id: "hr", label: "HR Laptop", sub: "Sensitive files", x: 495, y: 170 },
      { id: "idp", label: "Identity", sub: "SSO", x: 495, y: 350 },
      { id: "payroll", label: "Payroll DB", sub: "Crown jewel", x: 720, y: 260, target: true }
    ],
    edges: [["internet", "mail"], ["internet", "vpn"], ["mail", "hr"], ["vpn", "idp"], ["idp", "payroll"], ["hr", "payroll"], ["hr", "idp"]],
    redSteps: [
      ["phish", "Internet", "Mail Portal", "Fake login lure captures a weak employee password.", 16],
      ["login", "Internet", "VPN", "Credential stuffing succeeds without MFA.", 25],
      ["privilege", "VPN", "Identity", "Attacker searches for privileged group membership.", 32],
      ["impact", "Identity", "Payroll DB", "Attacker requests payroll export using stolen session.", 36]
    ],
    blueSteps: [
      ["detect", "Mail Portal", "Detect impossible login and repeated password failures.", 20],
      ["contain", "VPN", "Revoke session and challenge user with MFA.", 28],
      ["hunt", "Identity", "Search for new tokens and suspicious group lookups.", 40],
      ["report", "Payroll DB", "Create account takeover incident summary.", 50]
    ]
  },
  "insider-leak": {
    summary: "AI defender hunts for unusual data access by a trusted internal user.",
    nodes: [
      { id: "employee", label: "Employee", sub: "Trusted user", x: 115, y: 260 },
      { id: "crm", label: "CRM", sub: "Customer data", x: 300, y: 175 },
      { id: "git", label: "Code Repo", sub: "Source code", x: 300, y: 345 },
      { id: "files", label: "File Server", sub: "Shared drive", x: 520, y: 175 },
      { id: "cloud", label: "Cloud Bucket", sub: "Export path", x: 520, y: 345 },
      { id: "archive", label: "Data Archive", sub: "Crown jewel", x: 735, y: 260, target: true }
    ],
    edges: [["employee", "crm"], ["employee", "git"], ["crm", "files"], ["git", "cloud"], ["files", "archive"], ["cloud", "archive"], ["files", "cloud"]],
    redSteps: [
      ["access", "Employee", "CRM", "User queries unusually large customer lists.", 10],
      ["collect", "CRM", "File Server", "Bulk exports are compressed into shared storage.", 22],
      ["stage", "File Server", "Cloud Bucket", "Data staged in an external cloud bucket.", 32],
      ["impact", "Cloud Bucket", "Data Archive", "Archive access requested outside business hours.", 34]
    ],
    blueSteps: [
      ["detect", "CRM", "Baseline model flags abnormal query volume.", 18],
      ["contain", "File Server", "Limit file share access and preserve evidence.", 28],
      ["block", "Cloud Bucket", "Block outbound transfer and rotate access key.", 42],
      ["report", "Data Archive", "Generate insider-risk investigation report.", 52]
    ]
  }
};

const state = {
  scenarioKey: "web-breach",
  turn: 0,
  running: false,
  timer: null,
  compromised: new Set(),
  protected: new Set(),
  activeEdges: [],
  events: [],
  alerts: [],
  detectedAt: null,
  risk: 34,
  redProgress: 0,
  blueProgress: 0
};

const el = {
  scenarioSelect: document.querySelector("#scenarioSelect"),
  runBtn: document.querySelector("#runBtn"),
  stepBtn: document.querySelector("#stepBtn"),
  resetBtn: document.querySelector("#resetBtn"),
  reportBtn: document.querySelector("#reportBtn"),
  graph: document.querySelector("#attackGraph"),
  riskScore: document.querySelector("#riskScore"),
  riskMeter: document.querySelector("#riskMeter"),
  redProgress: document.querySelector("#redProgress"),
  redMeter: document.querySelector("#redMeter"),
  blueProgress: document.querySelector("#blueProgress"),
  blueMeter: document.querySelector("#blueMeter"),
  detectTime: document.querySelector("#detectTime"),
  statusNote: document.querySelector("#statusNote"),
  scenarioSummary: document.querySelector("#scenarioSummary"),
  turnCount: document.querySelector("#turnCount"),
  redState: document.querySelector("#redState"),
  blueState: document.querySelector("#blueState"),
  redThought: document.querySelector("#redThought"),
  blueThought: document.querySelector("#blueThought"),
  redPlan: document.querySelector("#redPlan"),
  bluePlan: document.querySelector("#bluePlan"),
  timeline: document.querySelector("#timeline"),
  alerts: document.querySelector("#alerts"),
  eventCount: document.querySelector("#eventCount"),
  alertCount: document.querySelector("#alertCount"),
  patchWeb: document.querySelector("#patchWeb"),
  mfaAdmins: document.querySelector("#mfaAdmins"),
  segmentDb: document.querySelector("#segmentDb"),
  reportDialog: document.querySelector("#reportDialog"),
  reportText: document.querySelector("#reportText"),
  closeReport: document.querySelector("#closeReport"),
  copyReport: document.querySelector("#copyReport")
};

function scenario() {
  return scenarios[state.scenarioKey];
}

function reset() {
  stop();
  state.turn = 0;
  state.compromised = new Set();
  state.protected = new Set();
  state.activeEdges = [];
  state.events = [];
  state.alerts = [];
  state.detectedAt = null;
  state.risk = baseRisk();
  state.redProgress = 0;
  state.blueProgress = 0;
  renderAll();
}

function baseRisk() {
  let risk = 34;
  if (el.patchWeb.checked) risk -= 9;
  if (el.mfaAdmins.checked) risk -= 11;
  if (el.segmentDb.checked) risk -= 10;
  return Math.max(8, risk);
}

function stop() {
  state.running = false;
  clearInterval(state.timer);
  el.runBtn.innerHTML = '<span class="icon play-icon"></span>Run';
}

function run() {
  if (state.running) {
    stop();
    return;
  }
  state.running = true;
  el.runBtn.textContent = "Pause";
  state.timer = setInterval(() => {
    step();
    if (state.turn >= 8) stop();
  }, 1250);
}

function step() {
  if (state.turn >= 8) return;
  state.turn += 1;
  const data = scenario();
  const redIndex = Math.min(Math.floor((state.turn - 1) / 2), data.redSteps.length - 1);
  const blueIndex = Math.max(0, Math.min(Math.floor((state.turn - 2) / 2), data.blueSteps.length - 1));

  if (state.turn % 2 === 1) executeRed(data.redSteps[redIndex]);
  if (state.turn >= 2 && state.turn % 2 === 0) executeBlue(data.blueSteps[blueIndex]);

  state.redProgress = Math.min(100, redIndex * 24 + (state.turn % 2 === 1 ? 18 : 24));
  state.blueProgress = Math.min(100, state.turn >= 2 ? blueIndex * 23 + 20 : 0);
  state.risk = calculateRisk();
  renderAll();
}

function executeRed(stepData) {
  const [stateName, fromLabel, toLabel, detail] = stepData;
  const from = findNodeByLabel(fromLabel);
  const to = findNodeByLabel(toLabel);
  if (to) state.compromised.add(to.id);
  if (from && to) state.activeEdges = [{ from: from.id, to: to.id, type: "red" }];
  state.events.unshift({ type: "red", title: `Red Team: ${capitalize(stateName)}`, detail });
  if (stateName === "impact" || stateName === "exploit" || stateName === "privilege") {
    state.alerts.unshift({ level: "high", title: `High-risk ${stateName}`, detail });
  }
}

function executeBlue(stepData) {
  const [stateName, nodeLabel, detail] = stepData;
  const node = findNodeByLabel(nodeLabel);
  if (node) state.protected.add(node.id);
  if (!state.detectedAt) state.detectedAt = `Turn ${state.turn}`;
  state.activeEdges = state.activeEdges.map((edge) => ({ ...edge, type: "blue" }));
  state.events.unshift({ type: "blue", title: `Blue Team: ${capitalize(stateName)}`, detail });
  state.alerts.unshift({ level: stateName === "detect" ? "medium" : "low", title: `Response: ${stateName}`, detail });
}

function calculateRisk() {
  const defenseBonus = Number(el.patchWeb.checked) * 8 + Number(el.mfaAdmins.checked) * 10 + Number(el.segmentDb.checked) * 12;
  const attackPressure = state.compromised.size * 12 + state.redProgress * 0.28;
  const containment = state.protected.size * 9 + state.blueProgress * 0.22;
  return clamp(Math.round(34 + attackPressure - containment - defenseBonus), 6, 99);
}

function renderAll() {
  const data = scenario();
  el.scenarioSummary.textContent = data.summary;
  el.turnCount.textContent = state.turn;
  el.riskScore.textContent = state.risk;
  el.riskMeter.style.width = `${state.risk}%`;
  el.redProgress.textContent = `${state.redProgress}%`;
  el.redMeter.style.width = `${state.redProgress}%`;
  el.blueProgress.textContent = `${state.blueProgress}%`;
  el.blueMeter.style.width = `${state.blueProgress}%`;
  el.detectTime.textContent = state.detectedAt || "--";
  el.statusNote.textContent = statusNote();
  renderPlans();
  renderGraph();
  renderTimeline();
  renderAlerts();
}

function renderPlans() {
  const data = scenario();
  const redIndex = Math.min(Math.floor(Math.max(state.turn - 1, 0) / 2), data.redSteps.length - 1);
  const blueIndex = Math.max(0, Math.min(Math.floor(Math.max(state.turn - 2, 0) / 2), data.blueSteps.length - 1));
  const red = data.redSteps[redIndex];
  const blue = data.blueSteps[blueIndex];
  el.redState.textContent = capitalize(red[0]);
  el.blueState.textContent = state.turn < 2 ? "Monitoring" : capitalize(blue[0]);
  el.redThought.textContent = red[3];
  el.blueThought.textContent = state.turn < 2 ? "Watching baseline activity and waiting for suspicious patterns." : blue[2];
  el.redPlan.innerHTML = data.redSteps.map((item, index) => `<li class="${index === redIndex ? "active" : ""}">${item[0]} ${item[2]}</li>`).join("");
  el.bluePlan.innerHTML = data.blueSteps.map((item, index) => `<li class="${index === blueIndex && state.turn >= 2 ? "active" : ""}">${item[0]} ${item[1]}</li>`).join("");
}

function renderGraph() {
  const data = scenario();
  const edges = data.edges.map(([from, to]) => {
    const a = data.nodes.find((node) => node.id === from);
    const b = data.nodes.find((node) => node.id === to);
    const active = state.activeEdges.find((edge) => edge.from === from && edge.to === to);
    const cls = active ? `edge active-${active.type}` : "edge";
    return `<line class="${cls}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"></line>`;
  }).join("");

  const nodes = data.nodes.map((node) => {
    const classes = ["node"];
    if (state.compromised.has(node.id)) classes.push("compromised");
    if (state.protected.has(node.id)) classes.push("protected");
    if (node.target) classes.push("target");
    return `
      <g class="${classes.join(" ")}" transform="translate(${node.x} ${node.y})">
        <circle r="50"></circle>
        <text y="-5">${node.label}</text>
        <text class="sub" y="18">${node.sub}</text>
      </g>`;
  }).join("");

  el.graph.innerHTML = `<defs><filter id="softGlow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="5" result="blur"></feGaussianBlur><feMerge><feMergeNode in="blur"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge></filter></defs>${edges}${nodes}`;
}

function renderTimeline() {
  el.eventCount.textContent = `${state.events.length} events`;
  el.timeline.innerHTML = state.events.length ? state.events.map((event) => `
    <article class="event ${event.type}">
      <b>${event.title}</b>
      <span>${event.detail}</span>
    </article>`).join("") : `<article class="event system"><b>System ready</b><span>Press Run or Step to begin the exercise.</span></article>`;
}

function renderAlerts() {
  el.alertCount.textContent = `${state.alerts.length} alerts`;
  el.alerts.innerHTML = state.alerts.length ? state.alerts.map((alert) => `
    <article class="alert ${alert.level}">
      <b>${alert.title}</b>
      <span>${alert.detail}</span>
    </article>`).join("") : `<article class="alert low"><b>No active alerts</b><span>Blue Team is monitoring the environment.</span></article>`;
}

function statusNote() {
  if (state.turn === 0) return "Ready for simulation";
  if (state.risk >= 75) return "Critical pressure";
  if (state.blueProgress > state.redProgress) return "Containment gaining";
  if (state.turn >= 8) return "Exercise complete";
  return "Exercise in progress";
}

function generateReport() {
  const data = scenario();
  const finalStatus = state.risk >= 70 ? "High residual risk" : state.risk >= 40 ? "Moderate residual risk" : "Contained";
  const topEvents = state.events.slice(0, 6).reverse().map((event) => `- ${event.title}: ${event.detail}`).join("\n");
  const mitigations = [
    el.patchWeb.checked ? "Web server patching is enabled." : "Patch exposed web services and remove unnecessary remote access.",
    el.mfaAdmins.checked ? "Admin MFA is enabled." : "Enforce MFA for privileged and remote access accounts.",
    el.segmentDb.checked ? "Database segmentation is enabled." : "Segment crown-jewel systems from ordinary workstation paths.",
    "Keep detection rules mapped to MITRE ATT&CK and tune thresholds after every exercise."
  ].join("\n- ");

  return `CyberArena AI Incident Report

Scenario: ${el.scenarioSelect.options[el.scenarioSelect.selectedIndex].text}
Status: ${finalStatus}
Enterprise Risk Score: ${state.risk}/100
Red Team Progress: ${state.redProgress}%
Blue Team Containment: ${state.blueProgress}%
Detection Time: ${state.detectedAt || "Not detected yet"}

Executive Summary:
${data.summary} The Red Team AI attempted to progress through the simulated network while the Blue Team AI correlated events, raised alerts, and applied containment actions.

Key Timeline:
${topEvents || "- No exercise events have been generated yet."}

Recommended Actions:
- ${mitigations}

MITRE ATT&CK Mapping:
- Reconnaissance
- Initial Access
- Credential Access
- Lateral Movement
- Collection
- Exfiltration or Impact
`;
}

function findNodeByLabel(label) {
  return scenario().nodes.find((node) => node.label === label);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

el.runBtn.addEventListener("click", run);
el.stepBtn.addEventListener("click", step);
el.resetBtn.addEventListener("click", reset);
el.scenarioSelect.addEventListener("change", () => {
  state.scenarioKey = el.scenarioSelect.value;
  reset();
});
[el.patchWeb, el.mfaAdmins, el.segmentDb].forEach((input) => input.addEventListener("change", () => {
  state.risk = calculateRisk();
  renderAll();
}));
el.reportBtn.addEventListener("click", () => {
  el.reportText.textContent = generateReport();
  el.reportDialog.showModal();
});
el.closeReport.addEventListener("click", () => el.reportDialog.close());
el.copyReport.addEventListener("click", async () => {
  await navigator.clipboard.writeText(el.reportText.textContent);
  el.copyReport.textContent = "Copied";
  setTimeout(() => { el.copyReport.textContent = "Copy Report"; }, 1200);
});

reset();
