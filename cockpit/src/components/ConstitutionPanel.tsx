import { useCallback, useEffect, useState } from "react";
import { fetchConstitution } from "../api/daedalusClient";
import type { BeingInvariantReport } from "../shared/daedalus/beingConstitution";
import "./ConstitutionPanel.css";

export function ConstitutionPanel() {
  const [report, setReport] = useState<BeingInvariantReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchConstitution();
      setReport(data as BeingInvariantReport);
    } catch (e: unknown) {
      setReport(null);
      setError(e instanceof Error ? e.message : "Failed to load constitution report.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className="constitution-panel">
      <div className="constitution-panel__header">
        <h2 className="constitution-panel__title">Being Constitution</h2>
        <button type="button" className="constitution-panel__refresh" onClick={() => void load()}>
          Refresh
        </button>
      </div>

      {loading && <p className="constitution-panel__muted">Loading…</p>}
      {error && <p className="constitution-panel__error">{error}</p>}

      {report && !loading && (
        <>
          <div className="constitution-panel__summary" role="status">
            <span className="constitution-panel__summary-label">Overall</span>
            <span
              className={
                report.allPassed
                  ? "constitution-panel__badge constitution-panel__badge--ok"
                  : "constitution-panel__badge constitution-panel__badge--fail"
              }
              aria-label={report.allPassed ? "All checks passed" : "Some checks failed"}
            >
              {report.allPassed ? "✓" : "✗"}
            </span>
            {!report.allPassed && (
              <span className="constitution-panel__failed-count">
                {report.failedCount} failed
              </span>
            )}
          </div>

          <ul className="constitution-panel__checks">
            {report.checks.map((check) => (
              <li key={check.name} className="constitution-panel__check">
                <div className="constitution-panel__check-row">
                  <span
                    className={
                      check.passed
                        ? "constitution-panel__mark constitution-panel__mark--ok"
                        : "constitution-panel__mark constitution-panel__mark--fail"
                    }
                    aria-hidden
                  >
                    {check.passed ? "✓" : "✗"}
                  </span>
                  <span className="constitution-panel__check-name">{check.name}</span>
                  <span className="constitution-panel__check-status">
                    {check.passed ? "passed" : "failed"}
                  </span>
                </div>
                {!check.passed && check.detail && (
                  <p className="constitution-panel__check-detail">{check.detail}</p>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
