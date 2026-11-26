# JARVIS --- Ultimate Master Blueprint

**Iron Man / Avengers-inspired Personal AI Operating System**\
**Architecture:** Local-first · Multimodal · Multi-agent · Secure ·
Observable · Production-oriented\
**Document status:** Target architecture and implementation blueprint\
**Version:** 1.0\
**Date:** 2026-11-26

------------------------------------------------------------------------

## 0. Executive Summary

This document defines a practical engineering blueprint for building
JARVIS: a personal AI operating system inspired by the fictional
assistant in *Iron Man* and *Avengers: Endgame*.

JARVIS is not merely a chatbot. It is a modular platform that combines:

-   Natural-language and voice interaction
-   Multimodal image and screen understanding
-   Context-aware conversation and governed long-term memory
-   Model routing and provider abstraction
-   Multi-agent task planning and orchestration
-   Controlled tool, browser, desktop, and terminal interaction
-   Software engineering assistance
-   Knowledge retrieval and document intelligence
-   Smart-environment integrations
-   Identity, authorization, policy enforcement, and audit
-   Monitoring, deployment, backup, and disaster recovery

**Important engineering constraint:** No real system can guarantee 100%
capability or availability in every environment. "Production-ready" must
be demonstrated through implementation evidence, test results,
operational controls, and explicit acceptance criteria. A planned
feature is not a completed feature; a mock is not a real integration; an
unexecuted test is not a passing test.

### 0.1 Product principles

1.  Local-first inference and data processing by default.
2.  Cloud providers are opt-in, explicitly configured, and
    policy-controlled.
3.  Default-deny authorization and least privilege.
4.  Human approval for consequential or irreversible actions.
5.  Durable task state, bounded execution, cancellation, and recovery.
6.  Typed, versioned contracts between modules.
7.  Reuse existing trusted infrastructure and implementations before
    adding new systems.
8.  Modular architecture; do not introduce microservices without a
    measured reason.
9.  Observable behavior and auditable decisions.
10. Documentation and claims must match verified runtime behavior.

------------------------------------------------------------------------

# 1. Product Vision and Scope

## 1.1 Target experience

A user should be able to interact with JARVIS through web, desktop,
mobile, and voice interfaces; ask questions; provide images or
documents; delegate bounded tasks; inspect progress; approve sensitive
actions; and receive verified results.

Example:

> "JARVIS, inspect my development environment, identify failing
> services, review the latest project changes, and prepare a remediation
> plan."

Expected behavior:

1.  Authenticate the user and establish tenant/session context.
2.  Parse intent and constraints.
3.  Retrieve only authorized context.
4.  Build a bounded execution plan.
5.  Evaluate the plan against policy.
6.  Execute permitted read-only inspections.
7.  Request approval before mutating operations.
8.  Collect tool outputs and evidence.
9.  Validate findings and distinguish facts from hypotheses.
10. Persist permitted task history and produce a report.

## 1.2 Capability domains

  -----------------------------------------------------------------------
  ID                      Domain                  Target capabilities
  ----------------------- ----------------------- -----------------------
  J01                     Core Intelligence       Intent, context,
                                                  planning, routing,
                                                  validation

  J02                     Voice                   STT, TTS, streaming,
                                                  interruption, wake-word
                                                  option

  J03                     Vision                  Image, OCR, screen, and
                                                  authorized video
                                                  analysis

  J04                     Memory                  Working, episodic,
                                                  semantic, procedural,
                                                  project memory

  J05                     Agents                  Delegation, bounded
                                                  multi-agent workflows

  J06                     Computer Control        Browser, desktop, IDE,
                                                  terminal, file adapters

  J07                     Smart Environment       Home Assistant, MQTT,
                                                  Matter, sensors

  J08                     Engineering             Repository analysis,
                                                  coding, testing,
                                                  review, documentation

  J09                     Research                Search, source
                                                  evaluation, synthesis,
                                                  citations

  J10                     Security                Identity, policy,
                                                  threat detection, audit

  J11                     Knowledge               Document ingestion,
                                                  indexing, retrieval,
                                                  RAG

  J12                     Operations              Health, telemetry,
                                                  alerts, backup,
                                                  recovery
  -----------------------------------------------------------------------

## 1.3 Out of scope

Unless separately designed, risk-assessed, and authorized, JARVIS must
not provide:

-   Unrestricted administrative shell access
-   Autonomous destructive operations
-   Unbounded control of physical devices
-   Weaponized or harmful robotics functionality
-   Covert camera, microphone, or screen monitoring
-   Unrestricted financial transactions
-   Silent publication, deployment, DNS, credential, or production
    changes
-   Automatic transmission of private data to external AI providers

------------------------------------------------------------------------

# 2. Architecture Overview

## 2.1 Logical layers

  -----------------------------------------------------------------------
  Layer                   Components              Responsibilities
  ----------------------- ----------------------- -----------------------
  L0 --- Experience       Web, desktop, mobile,   User interaction
                          CLI, voice              

  L1 --- Identity         OIDC, sessions, MFA,    Authentication
                          device identity         

  L2 --- Gateway          API gateway, WebSocket, Request ingress
                          rate limits             

  L3 --- Intelligence     Context engine, model   AI capability
                          gateway, reasoning      

  L4 --- Orchestration    Planner, scheduler,     Workflow execution
                          task runtime            

  L5 --- Capabilities     Tools, MCP, connectors, Controlled external
                          adapters                actions

  L6 --- Knowledge        Memory, RAG, search,    Information retrieval
                          document processing     

  L7 --- Data             PostgreSQL, Redis,      Persistence
                          object storage          

  L8 --- Events           NATS JetStream or       Asynchronous messaging
                          equivalent              

  L9 --- Governance       Policy, approvals,      Control and
                          audit                   accountability

  L10 --- Operations      Telemetry, deployment,  Runtime operations
                          backup, recovery        
  -----------------------------------------------------------------------

## 2.2 Architecture decision: modular monolith first

Start with a modular monolith for the control plane. Keep domain
boundaries explicit and enforce them through packages, interfaces,
dependency rules, and tests.

Extract services only when there is a demonstrated need, such as:

-   Independent scaling or GPU scheduling
-   Stronger security isolation
-   Separate deployment cadence
-   Independent availability requirements
-   Distinct runtime or hardware dependencies

Do not create a distributed system merely to make the architecture
diagram look sophisticated.

## 2.3 Core architecture diagram

``` text
                  WEB / DESKTOP / MOBILE / VOICE
                                |
                         Secure API Gateway
                                |
                     Identity + Session Context
                                |
                  JARVIS Core / Application Layer
                                |
          +---------------------+----------------------+
          |                     |                      |
     Intelligence          Orchestration            Governance
          |                     |                      |
   Model Gateway          Task Runtime           Policy Engine
   Context Engine         Agent Registry         Approval Service
   Memory Retrieval       Scheduler              Audit Service
          |                     |
          +----------+----------+
                     |
             Capability Runtime
                     |
       +-------------+--------------+
       |             |              |
    Browser       Computer        Tool/MCP
    Adapter       Adapter         Adapters
       |             |              |
       +-------------+--------------+
                     |
             External Systems
                     |
       +-------------+--------------+
       |             |              |
   PostgreSQL      Redis       Event Broker
       |
  Object Storage / Vector Index
                     |
       Observability / Backup / DR
```

## 2.4 Technology recommendations

Select versions based on current compatibility, support lifecycle, and
security review at implementation time.

  -----------------------------------------------------------------------
  Area                    Recommended baseline    Notes
  ----------------------- ----------------------- -----------------------
  Backend                 Python 3.12+ / FastAPI  Typed domain and API
                                                  contracts

  Frontend                TypeScript / Next.js    Web control surface

  Desktop                 Tauri                   Desktop shell and
                                                  controlled native
                                                  adapters

  Mobile                  React Native            Cross-platform client

  AI gateway              LiteLLM or equivalent   Provider abstraction;
                                                  verify current
                                                  capabilities

  Local inference         Ollama and/or NVIDIA    Provider adapters, not
                          NIM                     application coupling

  Database                PostgreSQL              Authoritative
                                                  transactional store

  Vector search           pgvector                Start in PostgreSQL
                                                  unless scale proves
                                                  otherwise

  Cache                   Redis                   Transient state, cache,
                                                  rate limits

  Event streaming         NATS JetStream          Add only where durable
                                                  async events are needed

  Object storage          S3-compatible / MinIO   Documents and media

  Authentication          OIDC / OAuth 2.1 /      Use a mature identity
                          WebAuthn                provider

  Browser automation      Playwright              Isolated, authorized
                                                  browser contexts

  Speech                  Whisper-compatible STT; Benchmark language and
                          selected TTS engine     latency

  Observability           OpenTelemetry,          Metrics, traces,
                          Prometheus, Grafana     dashboards

  Deployment              Docker Compose          Kubernetes only when
                          initially               operationally justified

  IaC                     Terraform / OpenTofu    Reproducible
                                                  infrastructure
  -----------------------------------------------------------------------

These are recommendations, not mandatory dependencies. Preserve existing
working services where they satisfy the requirements.

------------------------------------------------------------------------

# 3. JARVIS Core Intelligence Engine

## 3.1 Responsibilities

The Core coordinates requests and does not directly bypass policy or
tool boundaries.

Required components:

1.  Request and intent classifier
2.  Conversation manager
3.  Context assembler
4.  Model router
5.  Task planner
6.  Task decomposer
7.  Tool registry
8.  Agent registry
9.  Policy decision point
10. Approval manager
11. Execution coordinator
12. Result validator
13. Recovery coordinator
14. Memory interface
15. Audit interface

## 3.2 Request lifecycle

``` text
RECEIVED
   |
AUTHENTICATED
   |
CLASSIFIED
   |
CONTEXT_ASSEMBLED
   |
PLANNED
   |
POLICY_EVALUATED
   +---- DENIED --------> REJECTED
   |
   +---- APPROVAL -----> WAITING_APPROVAL
   |                         |
   |                    APPROVED / DENIED
   |
READY
   |
EXECUTING
   |
VERIFYING
   +---- FAILED --------> RECOVERY / FAILED
   |
COMPLETED
```

Every transition must be validated and persisted. State changes must be
safe under retries and concurrent workers.

## 3.3 Task model

A task should record at least:

-   Task ID and tenant ID
-   Requesting principal and initiating client
-   Task type and risk classification
-   Parent task and correlation IDs
-   Plan version and plan digest
-   Current state and state version
-   Required capabilities
-   Approval references
-   Idempotency key
-   Start, deadline, and completion timestamps
-   Retry count and execution budget
-   Result references
-   Error classification
-   Evidence references
-   Retention classification

## 3.4 Reliability requirements

-   Bounded retries with exponential backoff and jitter
-   Absolute task deadline
-   Per-step timeout
-   Cancellation propagation
-   Idempotency for mutating operations
-   Durable checkpoints where appropriate
-   Dead-letter handling
-   Partial-result representation
-   Optimistic concurrency or transactional state transitions
-   No infinite agent loops or recursive delegation
-   Explicit resource budgets for tokens, time, memory, and tool calls

------------------------------------------------------------------------

# 4. Model Gateway and AI Provider Management

## 4.1 Design

All model access must pass through a provider gateway. Application
modules must not embed provider-specific credentials or APIs.

Responsibilities:

-   Provider registry
-   Model registry
-   Provider health
-   Capability metadata
-   Model routing
-   Request normalization
-   Streaming normalization
-   Usage accounting
-   Rate and budget limits
-   Retry and circuit-breaker policy
-   Data classification enforcement
-   Provider-specific error mapping

## 4.2 Routing policy

Route by task requirements, not just model name:

-   Language and modality
-   Context window
-   Tool-calling support
-   Structured output support
-   Latency
-   Locality and data classification
-   Hardware availability
-   Cost and quota
-   Provider health
-   User or organization policy

Cloud fallback must be disabled by default. If enabled, it must be
explicit, visible, logged, and constrained by data classification and
user policy.

## 4.3 Provider security

-   Keep credentials in a secret manager or protected OS credential
    store.
-   Never expose provider keys to frontend code.
-   Redact secrets from exceptions, logs, traces, and reports.
-   Scope credentials to the minimum required permissions.
-   Rotate credentials through an authorized process.
-   Use TLS and provider allowlists.
-   Prevent model output from changing provider policy.

------------------------------------------------------------------------

# 5. Voice Intelligence

## 5.1 Pipeline

``` text
Microphone / Push-to-talk
          |
     Audio Capture
          |
  VAD / Audio Preprocessing
          |
         STT
          |
   Intent + Context
          |
    JARVIS Core
          |
  Response Generation
          |
         TTS
          |
    Audio Streaming
```

## 5.2 Features

-   Thai and English speech recognition
-   Language detection and switching
-   Push-to-talk
-   Optional local wake-word detection
-   Voice activity detection
-   Streaming transcription
-   Streaming speech output
-   Interruption and barge-in
-   Conversation turn management
-   Device selection
-   Audio device health
-   Configurable voice and speaking rate
-   Explicit recording controls

## 5.3 Privacy and security

-   Wake-word detection is not authentication.
-   Voice biometrics must not be the sole authorization factor.
-   Show clear recording/microphone state.
-   Do not persist raw audio by default.
-   Obtain explicit consent for recording and retention.
-   Provide deletion and retention controls.
-   Apply permission checks before acting on voice commands.

## 5.4 Acceptance criteria

-   Real STT and TTS integration tested on supported hardware.
-   Thai and English quality benchmark documented.
-   Streaming, interruption, and disconnect tests pass.
-   Microphone permission and device failure behavior tested.
-   No unauthorized recording or command execution.

------------------------------------------------------------------------

# 6. Vision Intelligence

## 6.1 Capabilities

-   Image understanding
-   OCR and document extraction
-   Screen understanding
-   Video frame analysis
-   Visual question answering
-   Object and scene recognition
-   Diagram and chart interpretation
-   Visual search
-   Multimodal context assembly

## 6.2 Pipeline

``` text
Authorized Image / Screen / Video
               |
        Input Validation
               |
       Privacy Classification
               |
        Preprocessing / OCR
               |
      Vision Model / Analyzer
               |
       Structured Observations
               |
        Context + Provenance
               |
          JARVIS Core
```

## 6.3 Controls

-   Explicit camera and screen permissions
-   Visible capture indicators
-   No covert monitoring
-   No persistent recording by default
-   Configurable retention and deletion
-   Restrict access to captured media by tenant and role
-   Treat OCR and visual content as untrusted input
-   Do not treat text found in images as trusted system instructions

## 6.4 Acceptance criteria

-   Test supported image formats and size limits.
-   Test malformed and adversarial media.
-   Verify OCR and vision outputs retain provenance.
-   Verify permission revocation stops capture.
-   Verify media retention and deletion behavior.

------------------------------------------------------------------------

# 7. Memory and Knowledge Intelligence

## 7.1 Memory classes

  Memory         Purpose                      Suggested storage
  -------------- ---------------------------- -----------------------
  Working        Current task context         Redis / task store
  Conversation   Chat history                 PostgreSQL
  Episodic       Past events and outcomes     PostgreSQL
  Semantic       Facts and concepts           PostgreSQL + pgvector
  Procedural     Approved workflows           Versioned records
  Project        Repository/project context   PostgreSQL
  Preference     User-approved preferences    PostgreSQL

## 7.2 Memory lifecycle

``` text
Input
  |
Classification
  |
Consent / Policy Check
  |
Extraction
  |
Validation
  |
Deduplication
  |
Provenance + Confidence
  |
Persistence / Indexing
  |
Retrieval + Authorization
  |
Context Assembly
```

## 7.3 Required controls

-   Source and provenance tracking
-   Confidence and freshness metadata
-   Tenant and user ownership
-   Versioning
-   Deduplication
-   Expiration and retention
-   User-visible correction
-   Export and deletion
-   Access control at retrieval time
-   Prompt-injection isolation
-   No unrestricted autonomous memory writes

## 7.4 RAG

Implement hybrid retrieval where appropriate:

1.  Query normalization
2.  Authorization filter
3.  Keyword retrieval
4.  Vector retrieval
5.  Rank fusion
6.  Reranking where justified
7.  Source-aware context assembly
8.  Citation/provenance output

Never allow vector similarity to bypass authorization filters.

------------------------------------------------------------------------

# 8. Multi-Agent Ecosystem

## 8.1 Agent roles

  Agent           Responsibility
  --------------- ----------------------------------------
  Commander       Delegation and coordination
  Planner         Task decomposition and sequencing
  Research        Source discovery and synthesis
  Architecture    System design and ADR analysis
  Coding          Scoped implementation
  Review          Independent code review
  Security        Threat and vulnerability analysis
  DevOps          Infrastructure and operations analysis
  Database        Schema and query analysis
  QA              Test design and execution
  Documentation   Technical documentation
  Browser         Authorized browser workflows
  Computer        Authorized desktop workflows
  Vision          Image and screen analysis
  Knowledge       Document ingestion and retrieval
  Monitoring      Health and telemetry analysis

## 8.2 Agent contract

Each agent must define:

-   Stable identity and version
-   Input and output schemas
-   Allowed tools and capabilities
-   Data classification permissions
-   Maximum runtime
-   Token and tool-call budget
-   Concurrency limit
-   Delegation depth
-   Retry policy
-   Cancellation behavior
-   Audit requirements

## 8.3 Orchestration

Use explicit task graphs or bounded workflows. Avoid unconstrained
agent-to-agent conversations.

A typical workflow:

``` text
User Request
     |
Commander
     |
Planner
     |
Policy Evaluation
     |
+----+---------+----------+
|              |          |
Research     Security     QA
|              |          |
+--------------+----------+
               |
        Findings Merge
               |
       Human Approval
               |
       Scoped Execution
               |
      Independent Review
               |
       Result Verification
```

## 8.4 Agent safety

-   Default to read-only capabilities.
-   Separate implementer and reviewer identities.
-   Never self-approve consequential changes.
-   Limit delegation depth and concurrent tasks.
-   Treat tool output and retrieved content as untrusted.
-   Require policy checks at execution time, not only planning time.
-   Enforce sandboxing and resource quotas.

------------------------------------------------------------------------

# 9. Tool, MCP, Browser, and Computer Integration

## 9.1 Capability adapters

Provide typed adapters for:

-   Browser
-   Desktop
-   Terminal
-   IDE
-   File system
-   Git
-   Docker
-   Database
-   HTTP APIs
-   Smart-home platforms
-   MCP servers

## 9.2 Capability model

Use explicit capabilities such as:

-   `system.read`
-   `repository.read`
-   `repository.write`
-   `browser.read`
-   `browser.interact`
-   `terminal.allowlisted`
-   `container.inspect`
-   `database.read`
-   `database.mutate`
-   `deployment.request`
-   `deployment.execute`
-   `secrets.metadata.read`

Do not give every agent every capability.

## 9.3 Execution boundary

``` text
Proposed Action
      |
Schema Validation
      |
Identity / Tenant Check
      |
Capability Check
      |
Target Scope Validation
      |
Risk Classification
      |
Approval Requirement
      |
Sandboxed Execution
      |
Output Validation
      |
Audit + Evidence
```

## 9.4 Terminal policy

-   Prefer typed APIs over shell commands.
-   Use allowlisted executables and argument schemas.
-   Avoid shell interpolation.
-   Validate working directory and path boundaries.
-   Use process timeouts and process-tree termination.
-   Bound stdout/stderr and retained output.
-   Run with least privilege.
-   Isolate untrusted code.
-   Deny access to secrets and host control sockets unless explicitly
    required and approved.

## 9.5 Browser policy

-   Use isolated browser contexts.
-   Bind sessions to authenticated users.
-   Restrict navigation to approved domains where possible.
-   Protect against SSRF and local-network pivoting.
-   Do not expose cookies or session tokens to model context.
-   Require confirmation for purchases, submissions, account changes, or
    publication.
-   Record action evidence without recording sensitive page data
    unnecessarily.

------------------------------------------------------------------------

# 10. Software Engineering Intelligence

## 10.1 Capabilities

-   Repository discovery
-   Architecture analysis
-   Dependency inventory
-   Source search
-   Code generation
-   Refactoring
-   Unit and integration testing
-   Static analysis
-   Security scanning
-   CI/CD inspection
-   Documentation generation
-   Git workflow assistance
-   Release readiness assessment

## 10.2 Engineering workflow

``` text
DISCOVER
  |
READ POLICIES AND INSTRUCTIONS
  |
INSPECT WORKTREE AND BASELINE
  |
UNDERSTAND ARCHITECTURE
  |
THREAT MODEL
  |
PLAN MINIMAL PATCH
  |
APPROVAL WHEN REQUIRED
  |
IMPLEMENT
  |
TEST
  |
SECURITY SCAN
  |
INDEPENDENT REVIEW
  |
DOCUMENT
  |
RELEASE READINESS
```

## 10.3 Repository governance

For ZeaZ ecosystem work:

-   Read canonical `zeaz.md` first.
-   Read root and nested `AGENTS.md` files.
-   Preserve user modifications and untracked files.
-   Inspect all relevant repository instructions before editing.
-   Use a dedicated branch when required.
-   Do not push directly to protected default branches.
-   Do not force push or rewrite history.
-   Do not impersonate reviewers or fabricate approval.
-   Bind test and review evidence to exact commit SHA.
-   Do not merge until required checks and independent review pass.
-   Do not deploy or publish without explicit authorization.

Canonical policy reference:

`https://github.com/cvsz/zeaz/blob/main/zeaz.md`

------------------------------------------------------------------------

# 11. Smart Environment and IoT

## 11.1 Integration targets

-   Home Assistant
-   MQTT
-   Matter
-   Supported sensor gateways
-   Device registries
-   Environmental monitoring

## 11.2 Architecture

``` text
Device / Sensor
      |
Approved Gateway
      |
Device Registry
      |
Event Normalization
      |
Policy Evaluation
      |
Automation Engine
      |
Approved Device Adapter
      |
Device State Verification
```

## 11.3 Safety requirements

-   Device-specific allowlists
-   Explicit user permissions
-   Physical safety interlocks
-   Rate and frequency limits
-   State verification after commands
-   Manual override
-   Safe default state on communication failure
-   No dangerous physical actuation or weaponized control

------------------------------------------------------------------------

# 12. Dashboard and User Experience

## 12.1 Clients

-   Web application
-   Desktop application
-   Mobile application
-   CLI for operators
-   Voice interaction surface

## 12.2 Dashboard panels

  Panel            Content
  ---------------- -------------------------------------------
  Assistant        Conversation and command input
  System Status    Service and dependency health
  Model Status     Provider and model availability
  Agent Monitor    Active agents and resource usage
  Task Center      Queued, running, blocked, completed tasks
  Memory Center    Search, inspect, correct, delete
  Voice            Audio devices and voice state
  Vision           Authorized visual sessions
  Infrastructure   Hosts, containers, resources
  Security         Alerts, permissions, audit
  Environment      Connected devices and sensors
  Activity         Recent actions and events

## 12.3 Design requirements

-   Dark theme with restrained blue/cyan accents
-   Responsive layout
-   Keyboard navigation
-   Accessible contrast and labels
-   Reduced-motion support
-   Clear status and error states
-   Visible recording and execution indicators
-   Explicit approval UI
-   No decorative control that implies a nonexistent capability
-   No false "online", "secure", or "completed" indicators

A holographic visual style is a presentation choice. It must not be
coupled to domain logic.

------------------------------------------------------------------------

# 13. Data Architecture

## 13.1 Core entities

``` text
users
organizations
tenants
devices
sessions
roles
permissions
role_bindings

conversations
messages
memories
memory_sources
knowledge_documents
knowledge_chunks

providers
models
model_routes
usage_records

agents
agent_versions
agent_capabilities
agent_executions

tasks
task_steps
task_events
task_artifacts
approvals

tools
tool_versions
tool_permissions
tool_executions

automation_rules
automation_executions
iot_devices
iot_events

audit_events
security_events
system_metrics
```

## 13.2 Data requirements

-   UUID or equivalent non-guessable identifiers
-   Foreign-key integrity
-   Tenant-aware uniqueness and constraints
-   Explicit transaction boundaries
-   Schema versioning
-   Migration validation
-   Optimistic concurrency where appropriate
-   Idempotency keys
-   Bounded retention
-   Encryption for sensitive data
-   Backup and restore tests
-   No cross-tenant access
-   No secrets in application tables unless specifically designed for
    encrypted secret storage

## 13.3 PostgreSQL guidance

Use PostgreSQL as the authoritative transactional store. Add pgvector
for semantic retrieval if it meets scale and operational requirements.
Avoid introducing a separate vector database until measured constraints
justify it.

Redis is for transient workloads and caching, not the sole source of
truth for durable task state.

------------------------------------------------------------------------

# 14. API and Event Contracts

## 14.1 API groups

``` text
/api/v1/auth
/api/v1/assistant
/api/v1/conversations
/api/v1/memory
/api/v1/knowledge
/api/v1/agents
/api/v1/tasks
/api/v1/approvals
/api/v1/tools
/api/v1/models
/api/v1/voice
/api/v1/vision
/api/v1/automation
/api/v1/devices
/api/v1/security
/api/v1/audit
/api/v1/system
```

All APIs require authentication and authorization except explicitly
public health endpoints designed for that purpose.

## 14.2 Event types

``` text
assistant.requested
assistant.responded

task.created
task.started
task.completed
task.failed
task.cancelled

agent.started
agent.completed
agent.failed

approval.requested
approval.granted
approval.denied
approval.expired

tool.execution.started
tool.execution.completed
tool.execution.failed

memory.created
memory.updated
memory.deleted

security.alert.created
system.health.changed
```

## 14.3 Event envelope

Events should include, as applicable:

-   Event ID
-   Event type and schema version
-   Tenant ID
-   Actor ID
-   Correlation ID
-   Causation ID
-   Occurred-at timestamp
-   Producer identity
-   Payload
-   Data classification

Use idempotent consumers, bounded retries, dead-letter handling, and
schema compatibility checks.

------------------------------------------------------------------------

# 15. Security Architecture

## 15.1 Security controls

  Domain          Required controls
  --------------- -------------------------------------------------
  Identity        OIDC, MFA, WebAuthn/passkeys
  Authorization   RBAC, ABAC, capability scopes
  Sessions        Expiration, revocation, secure cookies
  Secrets         Vault or protected credential store
  API             Authentication, validation, rate limits
  Network         Segmentation, egress policy, TLS
  AI              Prompt-injection and data-exfiltration defenses
  Tools           Sandboxing and capability restrictions
  Data            Classification, encryption, retention
  Database        Least privilege and tenant isolation
  Audit           Tamper-evident records
  Supply chain    SBOM, dependency and secret scanning
  Containers      Non-root, minimal images, resource limits
  Recovery        Encrypted backups and restore drills

## 15.2 Threat model

Assess at minimum:

-   Prompt injection
-   Indirect prompt injection from documents and websites
-   SSRF
-   CSRF
-   XSS
-   SQL injection
-   Path traversal
-   Authentication bypass
-   Authorization bypass
-   Privilege escalation
-   Cross-tenant data leakage
-   Secret exfiltration
-   Malicious tool output
-   Supply-chain compromise
-   Model/provider compromise
-   Event replay and duplicate execution
-   Resource exhaustion
-   Agent runaway execution
-   Browser session theft
-   Unauthorized device control

## 15.3 Policy decision

Every action must be evaluated at execution time. The planner's
assertion that an action is safe is not authorization.

Decision outcomes:

-   `ALLOW`
-   `DENY`
-   `REQUIRE_APPROVAL`
-   `REQUIRE_REAUTHENTICATION`
-   `OUT_OF_SCOPE`

Default is deny when policy cannot be evaluated.

------------------------------------------------------------------------

# 16. Infrastructure and Deployment

## 16.1 Deployment topology

``` text
Clients
  |
TLS / Secure Gateway
  |
Identity and API Layer
  |
JARVIS Application
  +-- Core API
  +-- Agent Runtime
  +-- Model Gateway
  +-- Voice Adapter
  +-- Vision Adapter
  +-- Tool Runtime
  |
Internal Data Plane
  +-- PostgreSQL
  +-- Redis
  +-- Event Broker
  +-- Object Storage
  |
Observability
  +-- OpenTelemetry Collector
  +-- Metrics
  +-- Logs
  +-- Traces
  +-- Alerts
```

## 16.2 Operational requirements

-   Docker Compose development profile
-   Production deployment manifests
-   Persistent storage
-   Health and readiness probes
-   Resource limits and quotas
-   GPU scheduling when required
-   Internal-only database and model-server listeners
-   TLS and service authentication
-   Centralized logs and metrics
-   Secret injection at runtime
-   Automated encrypted backup
-   Restore verification
-   Rollback procedures
-   Disaster recovery runbooks

## 16.3 Kubernetes decision

Do not require Kubernetes for the first usable deployment. Introduce it
only when multi-node scheduling, availability, scaling, isolation, or
organizational operations justify its cost.

## 16.4 Network boundaries

-   Public ingress only to the intended gateway.
-   Databases, Redis, event brokers, and model servers remain private.
-   Restrict outbound network access.
-   Apply DNS and IP policy to tool execution.
-   Do not trust user-provided URLs or hostnames.
-   Enforce SSRF protections at the network and application layers.

------------------------------------------------------------------------

# 17. Observability and Operations

## 17.1 Required telemetry

-   Request rate and latency
-   Model latency and token usage
-   Provider availability and error rate
-   Task queue depth
-   Task duration and outcome
-   Agent concurrency and budget use
-   Tool execution latency and failures
-   Database health and connection pool
-   Cache hit ratio
-   Event lag and dead-letter count
-   CPU, memory, disk, and GPU utilization
-   Security and authorization denials

## 17.2 Correlation

Propagate trace and correlation identifiers across:

-   API requests
-   Model calls
-   Agent executions
-   Tool calls
-   Events
-   Database operations
-   Approval workflows

Never put secrets, raw credentials, or unnecessary private content in
telemetry.

## 17.3 Operations runbooks

Maintain runbooks for:

-   Service unavailable
-   Provider unavailable
-   GPU out of memory
-   Database unavailable
-   Event broker unavailable
-   Queue backlog
-   Stuck task
-   Agent runaway
-   Secret compromise
-   Suspected data leak
-   Backup failure
-   Restore procedure
-   Rollback procedure

------------------------------------------------------------------------

# 18. Backup, Recovery, and Data Lifecycle

## 18.1 Requirements

-   Define RPO and RTO with the system owner.
-   Encrypt backups.
-   Separate backup credentials from runtime credentials.
-   Store copies outside the primary failure domain.
-   Monitor backup completion.
-   Test restore on a schedule.
-   Verify database consistency after restore.
-   Document recovery dependencies.
-   Apply retention and deletion policy to backups.
-   Record restore evidence.

## 18.2 Recovery acceptance

A backup is not proven usable until a restore test has completed
successfully and the restored data has been validated.

------------------------------------------------------------------------

# 19. Testing Strategy

## 19.1 Test layers

1.  Unit tests
2.  Component tests
3.  API integration tests
4.  Database integration tests
5.  Event contract tests
6.  Provider adapter tests
7.  Voice pipeline tests
8.  Vision pipeline tests
9.  Agent execution tests
10. Authorization and tenant isolation tests
11. Prompt-injection tests
12. Browser and computer adapter tests
13. Concurrency tests
14. Cancellation and recovery tests
15. Load and stress tests
16. Backup and restore tests
17. Cross-platform tests
18. End-to-end tests

## 19.2 Test evidence

Every validation report must distinguish:

-   `PASS`
-   `FAIL`
-   `SKIPPED`
-   `BLOCKED`
-   `NOT VERIFIED`

Record exact command, environment, dependency versions, commit SHA,
start/end time, and relevant sanitized output.

Mocked provider tests must never be represented as real provider tests.

## 19.3 Initial quality gates

-   No unresolved Critical or High security findings.
-   No secrets in source, logs, reports, or artifacts.
-   Authorization tests pass.
-   Tenant isolation tests pass.
-   Task cancellation and timeouts work.
-   Resource limits are enforced.
-   Backup restore test passes.
-   Documentation matches implementation.
-   Required CI checks pass.
-   Independent review is complete where required.

------------------------------------------------------------------------

# 20. Repository and Project Organization

The following is a logical target, not an instruction to create every
repository immediately.

``` text
cvsz/
├── jarvis/                    # Core platform
│   ├── jarvis-core/
│   ├── jarvis-api/
│   ├── jarvis-orchestrator/
│   ├── jarvis-policy/
│   └── jarvis-events/
├── jarvis-ai/                 # Model and intelligence
│   ├── model-gateway/
│   ├── context-engine/
│   ├── memory-engine/
│   ├── rag-engine/
│   └── reasoning-engine/
├── jarvis-agents/             # Specialized agents
│   ├── commander/
│   ├── research/
│   ├── coding/
│   ├── security/
│   ├── devops/
│   └── quality/
├── jarvis-voice/              # Voice services
├── jarvis-vision/             # Vision services
├── jarvis-interface/          # Web, desktop, mobile
├── jarvis-integrations/       # Browser, computer, MCP, IoT
├── jarvis-infrastructure/     # Compose, IaC, monitoring, backup
└── jarvis-docs/               # Architecture, ADRs, API, operations
```

Before creating repositories or modules:

1.  Discover existing repositories and services.
2.  Identify ownership and maintenance model.
3.  Inspect reusable code and contracts.
4.  Preserve upstream attribution for forks and mirrors.
5.  Avoid duplicate implementations.
6.  Choose repository boundaries based on actual ownership and
    deployment needs.

------------------------------------------------------------------------

# 21. Implementation Roadmap

## Phase 0 --- Discovery and Governance

Deliverables:

-   Canonical policy and repository instructions read
-   Existing repository inventory
-   Infrastructure and service inventory
-   Worktree and branch baseline
-   Reusable component map
-   Current dependency map
-   Initial threat model
-   Architecture Decision Records
-   Test and validation baseline

Exit gate: architecture and implementation scope are based on verified
repository and runtime evidence.

## Phase 1 --- Core Platform

Implement:

-   Authentication integration
-   API foundation
-   PostgreSQL schema
-   Tenant boundaries
-   Policy engine
-   Approval service
-   Audit service
-   Health endpoints
-   Configuration and secret handling

Exit gate: core contracts, identity, authorization, and persistence
tests pass.

## Phase 2 --- Model Gateway and Intelligence

Implement:

-   Provider adapters
-   Model registry
-   Routing policy
-   Context assembly
-   Conversation service
-   Streaming response
-   Usage and budget accounting

Exit gate: local provider integration is verified; cloud fallback
remains disabled unless explicitly configured.

## Phase 3 --- Memory and Knowledge

Implement:

-   Memory model
-   Source provenance
-   Document ingestion
-   Chunking and indexing
-   Hybrid retrieval
-   Retention and deletion
-   Tenant-aware access filters

Exit gate: retrieval quality, authorization, deletion, and persistence
tests pass.

## Phase 4 --- Voice

Implement:

-   Audio capture
-   VAD
-   STT
-   Dialogue integration
-   TTS
-   Streaming
-   Interruption
-   Device management

Exit gate: real voice pipeline tested on supported hardware.

## Phase 5 --- Vision

Implement:

-   Image ingestion
-   OCR
-   Vision model adapter
-   Screen capture permissions
-   Multimodal context
-   Media retention controls

Exit gate: real vision integration and privacy controls verified.

## Phase 6 --- Agent Runtime

Implement:

-   Agent registry
-   Typed agent contracts
-   Planner and task graph
-   Durable execution
-   Capability permissions
-   Budgets and limits
-   Cancellation and recovery
-   Approval workflow

Exit gate: multi-agent workflows pass isolation, cancellation,
concurrency, and policy tests.

## Phase 7 --- Tool and Computer Integration

Implement:

-   Browser adapter
-   File adapter
-   Terminal adapter
-   Git adapter
-   Docker adapter
-   IDE integration
-   MCP integration

Exit gate: adapters run in scoped environments with verified permissions
and audit evidence.

## Phase 8 --- Engineering Intelligence

Implement:

-   Repository discovery
-   Architecture analysis
-   Code review
-   Test execution
-   Security scanning
-   Documentation workflows
-   Release readiness reports

Exit gate: repository operations preserve user work and comply with
governance.

## Phase 9 --- Smart Environment

Implement:

-   Device registry
-   Home Assistant adapter
-   MQTT adapter
-   Event normalization
-   Safe automation rules
-   Manual override

Exit gate: device permissions and safety interlocks pass tests.

## Phase 10 --- Dashboard and Clients

Implement:

-   Assistant interface
-   Task center
-   Agent monitor
-   Model status
-   Memory center
-   Security center
-   System health
-   Responsive web and desktop clients
-   Mobile client where required

Exit gate: all displayed controls perform real supported actions and
accessibility checks pass.

## Phase 11 --- Production Hardening

Implement and verify:

-   Security remediation
-   Load and stress tests
-   Concurrency tests
-   Backup and restore
-   Disaster recovery
-   Deployment and rollback
-   Observability and alerting
-   Cross-platform validation
-   Independent review
-   Release evidence

Exit gate: all applicable production acceptance criteria pass.

------------------------------------------------------------------------

# 22. Acceptance Criteria and SLO Targets

Targets below are initial design objectives. They are not claims of
current performance and must be measured in the target environment.

  Metric                                                              Initial target
  ------------------------------------------------- --------------------------------
  Core API availability                                                        99.9%
  Core API p95 latency, excluding model inference                           ≤ 300 ms
  Unauthorized privileged actions                                                  0
  Secret leakage                                                                   0
  Unbounded agent execution                                                        0
  Untracked production changes                                                     0
  Task state invariants                               100% in defined test scenarios
  Backup restore verification                                    Pass before release
  Critical security findings                             0 before production release

Additional acceptance requirements:

-   Every feature has a documented contract.
-   Every privileged action is authorized at execution time.
-   Every task has bounded execution and cancellation.
-   Every model provider is routed through the gateway.
-   Every persisted memory item has ownership and provenance.
-   Every external integration has timeout and error handling.
-   Every UI control has a real implementation.
-   Every production change has evidence and rollback planning.

------------------------------------------------------------------------

# 23. Master Implementation Directive

Use the following directive with an authorized coding agent after
repository access and canonical policy availability have been verified.

## Mission

Build a functional, secure, observable, maintainable, and verifiable
JARVIS Personal AI Operating System based on this blueprint.

## Mandatory execution sequence

`DISCOVER → READ POLICIES → INSPECT → ARCHITECT → THREAT MODEL → PLAN → IMPLEMENT → TEST → REVIEW → DOCUMENT → VERIFY`

## Mandatory rules

1.  Read the complete canonical `zeaz.md` policy and all applicable
    repository instructions before changes.
2.  Preserve all user modifications and untracked files.
3.  Inspect existing implementations before adding new components.
4.  Reuse existing services when appropriate.
5.  Keep local inference as the default.
6.  Keep cloud fallback disabled unless explicitly authorized.
7.  Use typed interfaces and versioned contracts.
8.  Use least privilege and default deny.
9.  Require approval for consequential actions.
10. Use bounded execution, retries, and resource budgets.
11. Never claim unexecuted tests passed.
12. Never treat mocks as production integrations.
13. Never expose secrets in logs, prompts, reports, or commits.
14. Never perform destructive operations without explicit authorization.
15. Do not deploy, publish, merge, alter DNS, or migrate production data
    without required authorization.
16. Use finite implementation iterations.
17. Keep implementation and independent review separate.
18. Bind evidence to exact repository and commit SHA.

## Definition of done

A component is complete only when:

-   Production implementation exists.
-   Contracts and ownership are defined.
-   Input validation is implemented.
-   Authorization is enforced.
-   Error handling is complete.
-   Failure paths are tested.
-   Unit and integration tests pass.
-   Security checks pass.
-   Documentation is updated.
-   Runtime behavior is verified.
-   Monitoring is available.
-   Recovery procedures are documented.

A production release additionally requires:

-   Required security findings resolved.
-   Independent review completed.
-   Exact commit verified.
-   Required CI checks passed.
-   Backup and restore verified.
-   Deployment authorization recorded.
-   Rollback readiness demonstrated.

## Final report

Produce:

1.  Repository inventory and exact HEAD SHA
2.  Policy and instruction files read
3.  Existing architecture and reusable components
4.  Target architecture and ADRs
5.  Implemented modules
6.  Changed files
7.  Security findings and remediation
8.  Test commands and results
9.  Runtime verification
10. Performance measurements
11. Deployment readiness
12. Backup and restore evidence
13. Blocked and unverified items
14. Residual risks
15. Next steps

Use `PASS`, `FAIL`, `SKIPPED`, `BLOCKED`, and `NOT VERIFIED` accurately.

**Final objective:** deliver real working capabilities, not a visual
demo or a collection of placeholders. Prioritize correctness, security,
operational reliability, and verifiable outcomes.

------------------------------------------------------------------------

# 24. Recommended Initial Configuration Decisions

Recommended starting choices:

  -----------------------------------------------------------------------
  Decision                            Recommendation
  ----------------------------------- -----------------------------------
  Deployment                          Hybrid architecture, local-first

  Inference                           Existing local infrastructure first

  Cloud fallback                      Disabled by default

  Hardware                            Discover and reuse existing
                                      hardware

  Interfaces                          Web + desktop + mobile + voice,
                                      phased

  Autonomy                            Autonomous read-only work; approval
                                      for consequential changes

  Integration                         Standalone core with governed ZeaZ
                                      integrations

  Database                            Existing PostgreSQL where suitable

  Architecture                        Modular monolith control plane

  Event system                        Add durable broker when justified

  Orchestration                       Durable, bounded task runtime

  Production release                  Evidence-backed gated release
  -----------------------------------------------------------------------

These are initial recommendations, not assumptions about the user's
current hardware, repository state, or installed services.

------------------------------------------------------------------------

# 25. Final Engineering Position

JARVIS should be developed as an integrated operating platform, not as a
single model with unrestricted access to a computer.

The differentiating capability is the combination of:

-   A dependable intelligence core
-   Governed memory and context
-   Reliable task orchestration
-   Specialized agents
-   Secure tool execution
-   Real multimodal interfaces
-   Verified integrations
-   Strong operational controls

The system is complete only to the extent that its capabilities have
been implemented and verified in the actual target environment. Any
unsupported, untested, or unavailable capability must remain clearly
marked as such.

**End of JARVIS Master Blueprint.**
