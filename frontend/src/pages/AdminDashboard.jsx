import { useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { useNavigate } from "react-router-dom";
import PeopleTab from "./admin/PeopleTab";
import SessionsTab from "./admin/SessionsTab";
import AttendanceTab from "./admin/AttendanceTab";
import GroupScanTab from "./admin/GroupScanTab";
import "./AdminDashboard.css";

const TABS = {
  people: { label: "People", component: PeopleTab },
  sessions: { label: "Sessions", component: SessionsTab },
  attendance: { label: "Attendance", component: AttendanceTab },
  groupscan: { label: "Group Scan", component: GroupScanTab },
};

export default function AdminDashboard() {
  const [tab, setTab] = useState("people");
  const { logout } = useAuth();
  const navigate = useNavigate();
  const ActiveTab = TABS[tab].component;

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Admin Dashboard</h1>
        <button
          onClick={() => {
            logout();
            navigate("/");
          }}
        >
          Log out
        </button>
      </header>

      <nav className="dashboard-tabs">
        {Object.entries(TABS).map(([key, { label }]) => (
          <button
            key={key}
            className={key === tab ? "tab active" : "tab"}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </nav>

      <main className="dashboard-content">
        <ActiveTab />
      </main>
    </div>
  );
}
