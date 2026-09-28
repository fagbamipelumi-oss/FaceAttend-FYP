import { createContext, useContext, useState } from "react";
import { login as apiLogin } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("admin_token"));

  async function login(username, password) {
    const data = await apiLogin(username, password);
    localStorage.setItem("admin_token", data.access_token);
    setToken(data.access_token);
  }

  function logout() {
    localStorage.removeItem("admin_token");
    setToken(null);
  }

  return (
    <AuthContext.Provider value={{ token, isAuthenticated: !!token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
