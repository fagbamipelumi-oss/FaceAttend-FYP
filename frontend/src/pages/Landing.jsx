import { Link } from "react-router-dom";
import "./Landing.css";

const PIPELINE_STEPS = [
  { title: "Consent + Enrollment", detail: "A participant consents, then 5-8 reference photos are captured." },
  { title: "Face Detection", detail: "Each photo is checked for exactly one detectable face before it is accepted." },
  { title: "Embedding", detail: "A 128-dimension face embedding is generated with a dlib ResNet encoder." },
  { title: "Recognition", detail: "A live capture is compared against every enrolled embedding by distance." },
  { title: "Attendance Log", detail: "A match below the threshold is logged once per person, per session." },
];

const TEAM = [
  { name: "Fagbami Michael Oluwapelumi", role: "220903094" },
  { name: "Oriji Boluwatife Oluwadamilare", role: "2209030150" },
];

export default function Landing() {
  return (
    <div className="landing">
      <header className="landing-hero">
        <h1>AI-Based Attendance System Using Face Recognition</h1>
        <p className="landing-subtitle">
          A Final Year Project that replaces manual roll-call with a face-recognition
          attendance pipeline, built to be measured, not just demonstrated.
        </p>
        <div className="landing-actions">
          <Link to="/admin/login" className="btn btn-primary">Admin Login</Link>
          <Link to="/kiosk" className="btn btn-secondary">Open Kiosk</Link>
        </div>
      </header>

      <section className="landing-section">
        <h2>The problem</h2>
        <p>
          Manual attendance taking in large lecture rooms is slow, easy to falsify by proxy
          ("signing in" for an absent classmate), and produces records that are tedious to
          audit after the fact. This project investigates whether a face-recognition pipeline,
          built entirely from proven open-source components rather than a model trained from
          scratch, can mark attendance reliably enough to be a practical classroom tool.
        </p>
      </section>

      <section className="landing-section">
        <h2>How it works</h2>
        <ol className="pipeline">
          {PIPELINE_STEPS.map((step, i) => (
            <li key={step.title} className="pipeline-step">
              <span className="pipeline-index">{i + 1}</span>
              <div>
                <h3>{step.title}</h3>
                <p>{step.detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="landing-section">
        <h2>Limitations and disclaimers</h2>
        <ul className="limitations">
          <li>
            Recognition accuracy was measured on a small, project-scale enrolled dataset. It is
            not validated at population scale, and face-recognition systems are well documented
            to perform unevenly across lighting conditions, skin tones, and demographic groups.
          </li>
          <li>
            Liveness detection (blink check) is a basic anti-spoofing measure, not a
            security-grade liveness system. It is not intended to resist a determined attacker.
          </li>
          <li>
            This system is a Final Year Project prototype, not a deployed production system. It
            has not undergone a formal security or privacy audit.
          </li>
          <li>
            Biometric data (enrollment photos and face embeddings) is collected only from
            participants who gave documented consent, and is used solely for this project.
          </li>
        </ul>
      </section>

      <footer className="landing-footer">
        <h2>Team</h2>
        <ul className="team-list">
          {TEAM.map((member) => (
            <li key={member.name}>{member.name} — {member.role}</li>
          ))}
        </ul>
        <p>Supervisor: Mr. Adetolaju</p>
      </footer>
    </div>
  );
}
