import { useCallback, useEffect, useState } from "react";

import { AISettings, api, SessionInfo } from "./api";
import AssistantPanel from "./components/AssistantPanel";
import AuditLog from "./components/AuditLog";
import ConnectForm from "./components/ConnectForm";
import TerminalView from "./components/TerminalView";

export default function App() {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [view, setView] = useState<"work" | "audit">("work");
  const [settings, setSettings] = useState<AISettings | null>(null);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const list = await api.sessions();
      setSessions(list);
      setActive((current) => (list.some((s) => s.id === current) ? current : (list[0]?.id ?? null)));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
    api.getSettings().then(setSettings).catch(() => {});
  }, [refresh]);

  async function close(id: string) {
    await api.close(id).catch(() => {});
    refresh();
  }

  async function changeMode(mode: AISettings["approval_mode"]) {
    if (!settings) return;
    setSettings(await api.putSettings({ ...settings, approval_mode: mode }));
  }

  const current = sessions.find((s) => s.id === active);

  return (
    <div className="app">
      <header>
        <h1>PIIS ModernTerminal</h1>
        <nav>
          <button className={view === "work" ? "tab active" : "tab"} onClick={() => setView("work")}>
            Терминал
          </button>
          <button className={view === "audit" ? "tab active" : "tab"} onClick={() => setView("audit")}>
            Журнал
          </button>
        </nav>
        {settings && (
          <label className="mode">
            Подтверждение
            <select
              value={settings.approval_mode}
              onChange={(e) => changeMode(e.target.value as AISettings["approval_mode"])}
            >
              <option value="confirm">все команды</option>
              <option value="readonly_auto">кроме show и ping</option>
            </select>
          </label>
        )}
      </header>

      <aside>
        <ConnectForm
          onConnected={(session) => {
            setActive(session.id);
            setView("work");
            refresh();
          }}
        />
        <h2>Сессии</h2>
        {error && <p className="error">{error}</p>}
        <ul className="sessions">
          {sessions.map((s) => (
            <li key={s.id} className={s.id === active ? "selected" : ""}>
              <button className="link" onClick={() => setActive(s.id)}>
                {s.protocol.toUpperCase()} {s.host}:{s.port}
              </button>
              <button className="secondary small" onClick={() => close(s.id)} title="Закрыть сессию">
                ×
              </button>
            </li>
          ))}
          {sessions.length === 0 && <li className="hint">Нет активных сессий</li>}
        </ul>
      </aside>

      <main>
        {view === "audit" ? (
          <AuditLog />
        ) : current ? (
          <div className="workspace">
            <TerminalView key={`term-${current.id}`} sessionId={current.id} />
            <AssistantPanel key={`chat-${current.id}`} sessionId={current.id} />
          </div>
        ) : (
          <p className="hint empty">Подключитесь к устройству, чтобы начать работу.</p>
        )}
      </main>
    </div>
  );
}
