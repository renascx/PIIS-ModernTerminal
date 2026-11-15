import { FormEvent, useState } from "react";

import { api, SessionInfo } from "../api";

type Props = { onConnected: (session: SessionInfo) => void };

export default function ConnectForm({ onConnected }: Props) {
  const [protocol, setProtocol] = useState<"ssh" | "telnet">("ssh");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const session = await api.connect({
        protocol,
        host: host.trim(),
        port: port ? Number(port) : undefined,
        username: username || undefined,
        password: password || undefined,
      });
      setPassword("");
      onConnected(session);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="connect" onSubmit={submit}>
      <h2>Новое подключение</h2>
      <label>
        Протокол
        <select value={protocol} onChange={(e) => setProtocol(e.target.value as "ssh" | "telnet")}>
          <option value="ssh">SSH</option>
          <option value="telnet">Telnet</option>
        </select>
      </label>
      <label>
        Адрес
        <input value={host} onChange={(e) => setHost(e.target.value)} placeholder="192.0.2.10" required />
      </label>
      <label>
        Порт
        <input
          value={port}
          onChange={(e) => setPort(e.target.value)}
          placeholder={protocol === "ssh" ? "22" : "23"}
          inputMode="numeric"
          pattern="[0-9]*"
        />
      </label>
      {protocol === "ssh" && (
        <>
          <label>
            Логин
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="off" />
          </label>
          <label>
            Пароль
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="off"
            />
          </label>
        </>
      )}
      {protocol === "telnet" && (
        <p className="hint">Логин и пароль для Telnet вводятся прямо в терминале.</p>
      )}
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={busy || !host.trim()}>
        {busy ? "Подключение…" : "Подключиться"}
      </button>
    </form>
  );
}
