import { useEffect, useState } from "react";
import { apiGet, apiPostJson, ApiError } from "../../api/client";

const todayIso = () => new Date().toISOString().slice(0, 10);

export default function SessionsTab() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ name: "", course: "", session_date: todayIso() });
  const [creating, setCreating] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      setSessions(await apiGet("/sessions"));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load sessions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await apiPostJson("/sessions", form);
      setForm({ name: "", course: "", session_date: todayIso() });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to create session.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <h2>Create a session</h2>
      <form onSubmit={handleCreate} className="inline-form">
        <input
          placeholder="Session name (e.g. CSC401 Lecture 3)"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
        <input
          placeholder="Course (optional)"
          value={form.course}
          onChange={(e) => setForm({ ...form, course: e.target.value })}
        />
        <input
          type="date"
          value={form.session_date}
          onChange={(e) => setForm({ ...form, session_date: e.target.value })}
          required
        />
        <button type="submit" disabled={creating}>
          {creating ? "Creating..." : "Create session"}
        </button>
      </form>

      {error && <p className="form-error">{error}</p>}

      <h2>Sessions</h2>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Course</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id}>
                <td>{s.id}</td>
                <td>{s.name}</td>
                <td>{s.course || "-"}</td>
                <td>{s.session_date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
