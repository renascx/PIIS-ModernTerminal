import { useCallback, useEffect, useState } from "react";

import { api, AuditRow } from "../api";

const DECISION = {
  auto: "авто",
  approved: "подтверждено",
  denied: "отклонено",
  confirmed: "подтверждено",
} as Record<string, string>;

export default function AuditLog() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api
      .audit(100)
      .then((data) => {
        setRows(data);
        setError("");
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(load, [load]);

  return (
    <div className="audit">
      <div className="audit-head">
        <h2>Журнал команд</h2>
        <button className="secondary" onClick={load}>
          Обновить
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>Время</th>
            <th>Команда</th>
            <th>Риск</th>
            <th>Решение</th>
            <th>Источник</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{new Date(r.time).toLocaleString("ru-RU")}</td>
              <td>
                <code>{r.command}</code>
              </td>
              <td>{r.risk}</td>
              <td>{DECISION[r.decision] ?? r.decision}</td>
              <td>{r.source === "assistant" ? "ассистент" : "вручную"}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={5} className="hint">
                Команд пока нет
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
