import { useEffect, useState } from "react";
import { apiGet, apiPostForm, ApiError } from "../../api/client";

export default function GroupScanTab() {
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    apiGet("/sessions").then(setSessions).catch(() => {});
  }, []);

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!sessionId) {
      setError("Select a session first.");
      e.target.value = "";
      return;
    }

    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append("session_id", sessionId);
      formData.append("file", file);
      const data = await apiPostForm("/recognize/group-scan", formData);
      setResult(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Group scan request failed.");
    } finally {
      setSubmitting(false);
      e.target.value = "";
    }
  }

  return (
    <div>
      <h2>Group scan</h2>
      <p>
        Upload one photo containing multiple people (e.g. a lecture hall). Every detected face
        is compared against enrolled people and attendance is marked for each match. There is
        no liveness check here -- this is for an admin reviewing a real photo, not a public
        walk-up kiosk.
      </p>

      <label>
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

      <div className="photo-upload-box">
        <input type="file" accept="image/*" onChange={handleFileChange} disabled={submitting} />
      </div>

      {error && <p className="form-error">{error}</p>}
      {submitting && <p>Processing...</p>}

      {result && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Face</th>
              <th>Person</th>
              <th>Distance</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {result.faces.length === 0 ? (
              <tr>
                <td colSpan={4}>No faces detected in this photo.</td>
              </tr>
            ) : (
              result.faces.map((f, i) => (
                <tr key={i}>
                  <td>#{i + 1}</td>
                  <td>{f.matched ? f.person_name : "Unrecognized"}</td>
                  <td>{f.distance !== null ? f.distance.toFixed(4) : "-"}</td>
                  <td>{f.attendance_status}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
