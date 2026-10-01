# MUTAWASSIM

**MUTAWASSIM** is an AI-powered system for detecting and verifying misleading religious content, prioritizing claims by risk, and generating evidence-based reports from trusted Islamic sources.

The system is designed to support da’wah organizations, researchers, and media teams by transforming religious content verification from a manual and reactive process into a structured, traceable, and source-grounded workflow.

---

## Overview

MUTAWASSIM processes batches of religious-related posts and analyzes them through a multi-stage pipeline.

The system:

1. Cleans and filters the input content.
2. Extracts verifiable religious claims.
3. Retrieves relevant evidence from trusted Islamic sources using RAG.
4. Verifies each claim based on the retrieved evidence.
5. Calculates a transparent risk score.
6. Generates a grounded report for da’wah organizations.
7. Displays the results through a dashboard.

The system does not independently issue fatwas or unsupported religious judgments. If sufficient evidence is unavailable, the claim is marked for further review instead of generating an unsupported answer.

---

## System Pipeline

```text
Input Batch
    │
    ▼
Data Cleaning
    │
    ▼
Religious Content Filtering
    │
    ▼
Claim Extraction
    │
    ▼
RAG Retrieval
    │
    ▼
Claim Verification
    │
    ▼
Risk Scoring
    │
    ▼
Grounded Report Generation
    │
    ▼
Dashboard
```

---

## Core Components

### 1. Data Cleaning & Filtering

Prepares incoming content before processing.

Responsibilities include:

- Removing duplicated or malformed records
- Normalizing text
- Handling missing values
- Identifying religious-related content
- Preparing clean input for claim extraction

---

### 2. Claim Extraction

Uses an LLM to extract statements that can be independently verified.

Examples include:

- Attributed hadith
- Religious statements
- Historical claims
- Incorrectly quoted verses
- Claims related to Islamic beliefs or concepts

Each extracted claim is converted into a structured format before verification.

Example:

```json
{
  "claim_id": "claim_001",
  "original_text": "...",
  "claim": "...",
  "category": "hadith"
}
```

---

### 3. RAG Retrieval

The retrieval layer searches trusted Islamic sources for evidence relevant to each extracted claim.

```text
Claim
  │
  ▼
Embedding
  │
  ▼
Semantic Retrieval
  │
  ▼
Relevant Source Chunks
  │
  ▼
Verification Context
```

Possible technologies:

- FAISS or Chroma
- Embedding models
- Semantic retrieval
- Grounded LLM generation

---

## Claim Verification

The verification engine receives the claim together with the retrieved evidence and produces a structured result.

```text
Claim + Retrieved Evidence
            │
            ▼
      Verification Engine
```

Example output:

```json
{
  "status": "misleading",
  "confidence": 0.91,
  "reason": "...",
  "sources": [
    {
      "title": "...",
      "reference": "..."
    }
  ]
}
```

Possible statuses include:

- Supported
- Misleading
- False
- Weak
- Needs Expert Review
- Insufficient Evidence

When reliable evidence is unavailable, the system avoids generating an unsupported judgment.

---

## Risk Scoring

After verification, each claim receives a transparent risk score.

The score can be based on factors such as:

```text
Risk Score =
Spread × Severity × Religious Sensitivity
```

Example:

```text
Spread:                0.8
Severity:              0.9
Religious Sensitivity: 0.7

Risk Score:            0.504
```

The purpose of the score is to help organizations prioritize the most urgent claims first.

---

## Report Generation

After verification and risk scoring, MUTAWASSIM generates an evidence-based report for the da’wah organization.

Each report may include:

- Original claim
- Verification result
- Risk score
- Explanation
- Supporting evidence
- Trusted sources
- Review status

The report generator relies only on retrieved evidence from approved sources to reduce hallucination and avoid unsupported religious judgments.

---

## Trusted Sources

MUTAWASSIM relies on approved Islamic references such as:

- Dorar Al-Saniyyah — Hadith
- Dorar Al-Saniyyah — Tafseer
- Dorar Al-Saniyyah — Aqeedah
- Dorar Al-Saniyyah — Fiqh
- Dorar Al-Saniyyah — History
- Quranpedia
- Shamela
- Dawa Center
- Islamic Content

---

## Project Structure

```text
mutawassim/
│
├── data/
│   ├── raw/
│   ├── cleaned/
│   ├── sources/
│   └── test_set/
│
├── ingestion/
│   ├── cleaner.py
│   └── classifier.py
│
├── extraction/
│   └── claim_extractor.py
│
├── retrieval/
│   ├── index_builder.py
│   ├── embeddings.py
│   └── retriever.py
│
├── verification/
│   └── verifier.py
│
├── scoring/
│   └── risk_score.py
│
├── reporting/
│   └── report_generator.py
│
├── evaluation/
│   └── evaluate.py
│
├── api/
│   └── main.py
│
├── dashboard/
│
└── tests/
```

---

## Tech Stack

### AI & NLP

- Python
- Large Language Models
- Embeddings
- RAG
- Prompt Engineering

### Retrieval

- FAISS / Chroma
- Vector Search
- Semantic Retrieval

### Backend

- FastAPI
- Python
- Pydantic

### Frontend

- React

### Evaluation

- Precision
- Recall
- F1 Score
- Verification Accuracy
- Source Citation Accuracy

---

## Development Responsibilities

### Developer 1 — Data Cleaning & Claim Extraction

Responsibilities:

- Dataset cleaning
- Text normalization
- Religious-content filtering
- Claim extraction
- Structured claim output

### Developer 2 — RAG & Verification

Responsibilities:

- Source indexing
- Embeddings
- Semantic retrieval
- Evidence retrieval
- Grounded verification
- Source attribution

### Developer 3 — Risk Scoring, Reporting & Evaluation

Responsibilities:

- Risk-score implementation
- Grounded report generation
- Verification evaluation
- Precision and Recall
- Citation validation

### Developer 4 — Backend, Dashboard & Integration

Responsibilities:

- FastAPI
- Pipeline integration
- Dashboard development
- API integration
- Error handling
- Demo workflow

---

## Evaluation

The system is evaluated using a labeled test set containing both valid and misleading religious claims.

Main metrics include:

- Claim Detection Precision
- Claim Detection Recall
- Verification Accuracy
- Source Citation Accuracy
- Risk Classification Accuracy

A verification result should only be considered valid when its cited evidence can be traced back to an approved source.

---

## Grounding & Hallucination Control

MUTAWASSIM follows a strict grounded-generation approach.

```text
No Reliable Evidence
        │
        ▼
No Unsupported Judgment
```

The model must not generate religious judgments based only on its internal knowledge.

If the retrieved context is insufficient, the claim is marked as:

```text
Needs Expert Review
```

or:

```text
Insufficient Evidence
```

---

## Design Principles

MUTAWASSIM is built around four core principles:

- **Traceability** — every result is linked to supporting evidence.
- **Grounding** — generated outputs rely on retrieved trusted sources.
- **Transparency** — risk scoring is clear and interpretable.
- **Human Oversight** — unresolved or sensitive claims are escalated for expert review.

---

## Goal

MUTAWASSIM aims to help da’wah organizations move from delayed and manual responses toward a proactive workflow where misleading religious claims can be detected, verified, prioritized, and reviewed with clear supporting evidence.
