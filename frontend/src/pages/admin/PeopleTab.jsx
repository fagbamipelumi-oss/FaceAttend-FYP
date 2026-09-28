import { useEffect, useState } from "react";
import { apiGet, apiPostForm, apiPostJson, ApiError } from "../../api/client";

export default function PeopleTab() {
  const [people, setPeople] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [form, setForm] = useState({ full_name: "", matric_number: "", email: "", consent_given: false });
  const [creating, setCreating] = useState(false);

  const [activePersonId, setActivePersonId] = useState(null);
  const [photoResults, setPhotoResults] = useState(null);
  const [uploading, setUploading] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const data = await apiGet("/people");
      setPeople(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load people.");
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
      const person = await apiPostJson("/people", form);
      setForm({ full_name: "", matric_number: "", email: "", consent_given: false });
      setActivePersonId(person.id);
      setPhotoResults(null);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to create person.");
    } finally {
      setCreating(false);
    }
  }

  async function handlePhotoUpload(e) {
    const files = Array.from(e.target.files || []);
    if (files.length === 0 || !activePersonId) return;
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      files.forEach((f) => formData.append("files", f));
      const result = await apiPostForm(`/people/${activePersonId}/photos`, formData);
      setPhotoResults(result);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to upload photos.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <div>
      <h2>Enroll a new person</h2>
      <form onSubmit={handleCreate} className="inline-form">
        <input
          placeholder="Full name"
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          required
        />
        <input
          placeholder="Matric number (optional)"
          value={form.matric_number}
          onChange={(e) => setForm({ ...form, matric_number: e.target.value })}
        />
        <input
          placeholder="Email (optional)"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        <label className="consent-check">
          <input
            type="checkbox"
            checked={form.consent_given}
            onChange={(e) => setForm({ ...form, consent_given: e.target.checked })}
          />
          Participant has given documented consent for biometric data collection.
        </label>
        <button type="submit" disabled={creating}>
          {creating ? "Creating..." : "Create person"}
        </button>
      </form>

      {activePersonId && (
        <div className="photo-upload-box">
          <h3>Upload enrollment photos for person #{activePersonId}</h3>
          <input type="file" accept="image/*" multiple onChange={handlePhotoUpload} disabled={uploading} />
          {photoResults && (
            <ul className="photo-results">
              {photoResults.results.map((r, i) => (
                <li key={i} className={r.accepted ? "accepted" : "rejected"}>
                  {r.filename}: {r.accepted ? "accepted" : `rejected (${r.reason})`}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {error && <p className="form-error">{error}</p>}

      <h2>Enrolled people</h2>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Matric No.</th>
              <th>Consent</th>
              <th>Photos enrolled</th>
            </tr>
          </thead>
          <tbody>
            {people.map((p) => (
              <tr
                key={p.id}
                onClick={() => {
                  setActivePersonId(p.id);
                  setPhotoResults(null);
                }}
                className={p.id === activePersonId ? "selected-row" : ""}
              >
                <td>{p.id}</td>
                <td>{p.full_name}</td>
                <td>{p.matric_number || "-"}</td>
                <td>{p.consent_given ? "Yes" : "No"}</td>
                <td>{p.enrolled_photo_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
