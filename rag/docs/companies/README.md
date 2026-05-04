# Company Knowledge Base

Add company-specific notes here as Markdown files named by ticker, for example:

- `AAPL.md`
- `MSFT.md`
- `NVDA.md`

Recommended structure:

```markdown
# AAPL

## Business Summary
...

## Durable Strengths
...

## Key Risks
...

## Portfolio Role
...
```

During ingestion, files in this folder are tagged as `doc_type=company_note` and `ticker=<FILENAME>`.

