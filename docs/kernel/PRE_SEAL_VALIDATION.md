# Pre‑Seal Validation & Cleanup

The Pre‑Seal Validation is the final structural audit before the Kernel Seal.

---

## Checks

1. **Shell health** — blocking  
2. **Kernel invariants** — blocking  
3. **Kernel status** — blocking  
4. **Orphan nodes** — warning  
5. **Epistemic unverified** — warning  
6. **Epistemic freshness** — warning  
7. **Continuity health** — warning  
8. **Sovereignty** — warning  

---

## Report

`PreSealReport` contains:

- issues  
- blockingCount  
- warningCount  
- passed  
- integrationCount  
- timestamp  

Seal allowed only when `passed === true`.

---

## Surfaces

- **Halo:** `preSealValidation`  
- **Throne:** `preSealPassed`, `preSealIssues`  

UI:

- Green "seal ready" badge  
- Red "blocking" badge  
- Gold "warnings" indicator  

---

## When to run

- Must run before the Seal  
- May run anytime  
- Skips during boot  

---

## Relationship to the Seal

This is the **only gate** before the Kernel Seal.  
