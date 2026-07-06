# Donna: Core Capabilities & Skills Inventory

This document maps out the specific execution skills available to the multi-agent orchestration framework. Each skill is tightly bound to an underlying Model Context Protocol (MCP) server or a verified hardware/software hook.

## 1. Security & Guardrail Skills (`security_guard`)
* **Prompt Validation:** Scans incoming raw text layers for systemic indicators of prompt injection, malicious system overrides, or jailbreak patterns.
* **Secure State Suspension:** Instantly flags unauthorized system mutations, terminates the active LangGraph execution frame, and writes a high-priority incident log.

## 2. Communications & Scheduling Skills (`comm_agent`)
* **Asynchronous Schedule Auditing:** Hooks into email and calendar data streams to identify structural overlaps or meeting conflicts.
* **Draft Synthesis:** Compiles contextual, professional email templates outlining scheduling anomalies and queues them into the Human-in-the-Loop (HITL) approval store.

## 3. Web Automation & Logistics Skills (`logistics_agent`)
* **Headless Browser Scraping:** Orchestrates dynamic Puppeteer MCP routines to launch browser contexts, parse nested DOM elements, and extract live pricing matrices for transport and entertainment tickets.
* **Structured Schema Extraction:** Normalizes raw web page data strings into structured JSON objects containing timestamps, transit nodes, and financial parameters.

## 4. Financial Ledger & Auditing Skills (`ledger_agent`)
* **Document Analysis:** Extracts key transactional text blocks from raw markdown invoices, receipt attachments, or billing statements.
* **Immutable Transaction Appending:** Maps parsed transaction parameters to predefined categories and pushes a cryptographic record to the write-only analytics database.
* **Masked Authentication Gate:** Controls the execution bridge for all processes requiring sensitive verification; blocks runtime states until a hidden, password-masked token matches the local environment hash.