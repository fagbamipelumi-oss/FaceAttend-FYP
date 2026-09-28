import { useEffect, useMemo, useState } from "react";
import { apiGet, ApiError } from "../../api/client";

export default function AttendanceTab() {
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState("");
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiGet("/sessions").then(setSessions).catch(() => {});
  }, []);

  useEffect(() => {
    if (!sessionId) {
      setRecords([]);
      return;
    }
    setLoading(true);
    setError(null);
    apiGet("/attendance", { session_id: sessionId })
      .then(setRecords)
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Failed to load attendance."))
      .finally(() => setLoading(false));
  }, [sessionId]);

  const selectedSession = useMemo(
    () => sessions.find((s) => String(s.id) === String(sessionId)),
    [sessions, sessionId]
  );

  const sortedRecords = useMemo(
    () => [...records].sort((a, b) => a.person_name.localeCompare(b.person_name)),
    [records]
  );

  return (
    <div>
      <h2 className="no-print">Attendance review</h2>
      <label className="no-print">
        Session:{" "}
        <select value={sessionId} onChange={(e) => setSessionId(e.target.value)}>
          <option value="">Select a session</option>
          {sessions.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} ({s.session_date})
            </option>
          ))}
        </select>
      </label>

      {sessionId && records.length > 0 && (
        <button className="btn btn-secondary no-print" onClick={() => window.print()}>
          Print attendance sheet
        </button>
      )}

      {error && <p className="form-error no-print">{error}</p>}
      {loading && <p className="no-print">Loading...</p>}

      {sessionId && !loading && (
        <table className="data-table no-print">
          <thead>
            <tr>
              <th>Person</th>
              <th>Matric No.</th>
              <th>Email</th>
              <th>Timestamp</th>
              <th>Match distance</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {records.length === 0 ? (
              <tr>
                <td colSpan={6}>No attendance recorded for this session yet.</td>
              </tr>
            ) : (
              records.map((r) => (
                <tr key={r.id}>
                  <td>{r.person_name}</td>
                  <td>{r.matric_number || "-"}</td>
                  <td>{r.email || "-"}</td>
                  <td>{new Date(r.timestamp).toLocaleString()}</td>
                  <td>{r.match_distance.toFixed(4)}</td>
                  <td>{r.source}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}

      {/* Print-only view: hidden on screen, shown only by @media print in
          index.css. Full enrollment record per attendee (name, matric
          number, email) plus date/time, not the admin-diagnostic columns
          (match distance, source) from the on-screen table. */}
      {sessionId && selectedSession && (
        <div className="print-area">
          <h2>Attendance Sheet</h2>
          <p>
            <strong>{selectedSession.name}</strong>
            {selectedSession.course ? ` (${selectedSession.course})` : ""} —{" "}
            {selectedSession.session_date}
          </p>
          <table className="print-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Name</th>
                <th>Matric No.</th>
                <th>Email</th>
                <th>Date</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {sortedRecords.map((r, i) => {
                const ts = new Date(r.timestamp);
                return (
                  <tr key={r.id}>
                    <td>{i + 1}</td>
                    <td>{r.person_name}</td>
                    <td>{r.matric_number || "-"}</td>
                    <td>{r.email || "-"}</td>
                    <td>{ts.toLocaleDateString()}</td>
                    <td>{ts.toLocaleTimeString()}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="print-footer">
            Total present: {sortedRecords.length}. Printed {new Date().toLocaleString()}.
          </p>
        </div>
      )}
    </div>
  );
}
