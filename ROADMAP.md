# Roadmap

This template stays language-agnostic while providing production-grade **repository foundations**.

## Foundation

- [x] Repository documentation baseline
- [x] Security and contribution policies
- [x] Issue and pull request templates
- [x] CI and security workflow baseline
- [x] Dependabot configuration
- [x] Release guidance and release-note configuration
- [x] Docker and task-runner placeholders
- [x] Architecture/development/release documentation structure
- [x] Immutable SHA pinning for baseline GitHub Actions
- [x] Repository structure and local Markdown-link validation
- [x] GitHub administration apply/verify automation
- [x] Protected-default-branch policy baseline
- [x] ZEAZ cross-agent execution framework
- [x] Reusable AI guides/playbooks/prompts
- [x] Discovery-first skills/component/plugin catalog scaffold
- [x] Safe rollout guidance for existing repositories

## Reusable first-project startup

- [x] Identity bootstrap with dry-run, explicit apply, and idempotence
- [x] Safe ownership/security issue-link replacement
- [x] Optional project profiles and adoption guide
- [x] Bootstrap tests in baseline CI
- [x] Repository administration verification helper
- [ ] Validate production-capable per-stack adapters in generated repositories
- [ ] Add end-to-end fixture verification for each adopted stack

## Future optional modules

- [ ] Language-specific starter packs
- [ ] Infrastructure-as-code starter packs
- [ ] Kubernetes and Helm starter packs
- [ ] SBOM/provenance workflows
- [ ] Release signing and artifact attestation
- [ ] OpenSSF Scorecard workflow
- [ ] Container vulnerability scanning
- [ ] Documentation site starter
- [ ] Monorepo profile
- [ ] Service/API profile
- [ ] Web application profile
- [ ] Library/SDK profile
- [ ] Machine-readable skill catalog/version index when real catalog scale justifies it
- [ ] Benchmark/reference-set framework when there are real scenarios to measure

Generated repositories should adopt only modules appropriate to their stack, threat model, operating environment, and compliance needs.


## zjavis Blueprint Implementation Progress (cvsz/zjavis)

Progress against `javis-blueprint.md` section 21 (Implementation Roadmap):

| Phase | Domain | Status | Modules | Evidence |
|-------|--------|--------|---------|----------|
| Phase 0 | Discovery & Governance | COMPLETE | AGENTS.md, ZEAZ-INTRODUCTION.md, SECURITY.md, GOVERNANCE.md, CODEOWNERS | Repository contract in place |
| Phase 1 | Core Platform | COMPLETE | `src/jarvis/core/`, `src/jarvis/auth/`, `src/jarvis/db/`, `src/jarvis/api/` | 14 entities, Alembic `0001_initial_schema`, 205 tests pass |
| Phase 2 | Model Gateway & Intelligence | COMPLETE | `src/jarvis/ai/gateway.py`, `provider.py`, `context.py` | Local/OpenAI/Ollama adapters, routing, budget, usage |
| Phase 3 | Memory & Knowledge | COMPLETE | `src/jarvis/ai/memory.py` | CRUD, deduplication (SHA-256), search, retention |
| Phase 4 | Voice | STUB | `src/jarvis/ai/voice.py` | Feature-flagged (`JARVIS_VOICE_ENABLED=false`); requires audio hardware + STT/TTS credentials |
| Phase 5 | Vision | STUB | `src/jarvis/ai/vision.py` | Feature-flagged (`JARVIS_VISION_ENABLED=false`); requires GPU + vision model credentials |
| Phase 6 | Agent Runtime | COMPLETE | `src/jarvis/ai/agent_runtime.py`, `src/jarvis/approval/`, `src/jarvis/audit/` | Approval-gated execution, audit trail |
| Phase 6 (ext.) | Orchestration Engine | COMPLETE | `src/jarvis/orchestration/executor.py` | Timeout, retry+backoff+jitter, CancellationToken, idempotency, dead-letter |
| Phase 6 (ext.) | Policy Engine Enforcement | COMPLETE | `src/jarvis/api/main.py` | Execution-time PolicyEngine decisions on all mutating API routes |
| Phase 6 (ext.) | Idempotency | COMPLETE | `src/jarvis/api/tasks.py` | Idempotency key conflict detection on task creation |
| Phase 6 (ext.) | Streaming Resilience | COMPLETE | `src/jarvis/api/conversations.py` | SSE stream DB commit failure handling |
| Phase 7 | Tool & Computer Integration | NOT RUN | — | Browser, terminal, file, Git, Docker, MCP adapters not implemented |
| Phase 8 | Engineering Intelligence | NOT RUN | — | Repository analysis, coding, review, testing not implemented |
| Phase 9 | Smart Environment | STUB | `src/jarvis/ai/smart_environment.py` | Feature-flagged (`JARVIS_SMART_ENVIRONMENT_ENABLED=false`); requires IoT hardware + credentials |
| Phase 10 | Dashboard & Clients | NOT RUN | — | Web/desktop/mobile clients not implemented |
| Phase 11 | Production Hardening | PARTIAL | Security controls, observability metrics | Backup/restore, tracing, load testing, E2E not implemented |

GitHub delivery (Step 5 of master plan): PR #33 (orchestration engine + policy enforcement) BLOCKED by branch protection (base branch policy prohibits merge despite all required checks passing and independent approval). PR #31 (CODEOWNERS) BLOCKED by merge conflicts. PR #27 (tenant isolation) Changes Requested.
