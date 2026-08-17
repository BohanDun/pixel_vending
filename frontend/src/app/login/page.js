"use client";

import { useContext, useState } from "react";
import Image from "next/image";
import AuthContext from "../context/AuthContext";
import api from "../../lib/api";

const Login = () => {
  const { login } = useContext(AuthContext);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginMessage, setLoginMessage] = useState("");

  const [registerUsername, setRegisterUsername] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoginMessage("");
    try {
      await login(username, password);
    } catch (err) {
      const msg =
        (err &&
          err.response &&
          (err.response.data?.detail || err.response.data)) ||
        err.message ||
        "Login failed";
      setLoginMessage(msg);
    }
  };

  const handleRegister = (e) => {
    e.preventDefault();
    api
      .post("/auth/", {
        username: registerUsername,
        password: registerPassword,
      })
      .then(() => {
        setRegisterUsername("");
        setRegisterPassword("");
        setLoginMessage("");
        alert("Account created successfully");
      })
      .catch((err) => {
        const msg =
          (err &&
            err.response &&
            (err.response.data?.detail || err.response.data)) ||
          err.message ||
          "Register failed";
        alert(msg);
      });
  };

  return (
    <main className="auth-shell auth-shell-simple">
      <section className="auth-panel auth-panel-simple">
        <div className="auth-card auth-card-simple">
          <Image
            className="auth-logo"
            src="/assets/pixel-vending-logo.png"
            alt="Pixel Vending Simulator"
            width={384}
            height={256}
            priority
            unoptimized
          />
          <div className="auth-card-heading">
            <h1>Welcome back</h1>
            <p>Sign in to manage your vending world.</p>
          </div>
          {loginMessage && (
            <div className="alert alert-danger" role="alert">
              {loginMessage}
            </div>
          )}
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label htmlFor="username" className="form-label">Username</label>
              <input
                type="text"
                className="form-control"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>
            <div className="mb-4">
              <label htmlFor="password" className="form-label">Password</label>
              <input
                type="password"
                className="form-control"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            <button type="submit" className="btn btn-primary auth-submit">
              Sign in
            </button>
          </form>

          <div className="auth-divider"><span>New here?</span></div>

          <details className="register-details">
            <summary>Create account</summary>
            <form onSubmit={handleRegister}>
              <div className="mb-3">
                <label htmlFor="registerUsername" className="form-label">Username</label>
                <input
                  type="text"
                  className="form-control"
                  id="registerUsername"
                  value={registerUsername}
                  onChange={(e) => setRegisterUsername(e.target.value)}
                  autoComplete="username"
                  required
                />
              </div>
              <div className="mb-3">
                <label htmlFor="registerPassword" className="form-label">Password</label>
                <input
                  type="password"
                  className="form-control"
                  id="registerPassword"
                  value={registerPassword}
                  onChange={(e) => setRegisterPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>
              <button type="submit" className="btn btn-outline-primary w-100">
                Create account
              </button>
            </form>
          </details>
        </div>
      </section>
    </main>
  );
};

export default Login;
