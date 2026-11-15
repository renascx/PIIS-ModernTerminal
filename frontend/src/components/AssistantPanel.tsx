import { FormEvent, useEffect, useRef, useState } from "react";

import { AgentReply, api, Pending } from "../api";

type Message = { role: "user" | "assistant" | "system"; text: string };

const RISK_LABEL = { read_only: "чтение", config: "изменение", dangerous: "опасная" };

export default function AssistantPanel({ sessionId }: { sessionId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState<Pending[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages([]);
    setPending([]);
    api.pending(sessionId).then(setPending).catch(() => {});
  }, [sessionId]);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending]);

  const add = (message: Message) => setMessages((all) => [...all, message]);

  function showReply(reply: AgentReply) {
    if (reply.text) add({ role: "assistant", text: reply.text });
    setPending(reply.pending);
  }

  async function run(action: () => Promise<AgentReply>) {
    setBusy(true);
    try {
      showReply(await action());
    } catch (e) {
      add({ role: "system", text: (e as Error).message });
    } finally {
      setBusy(false);
    }
  }

  function send(event: FormEvent) {
    event.preventDefault();
    const message = text.trim();
    if (!message) return;
    setText("");
    add({ role: "user", text: message });
    run(() => api.chat(sessionId, message));
  }

  function decide(item: Pending, approve: boolean) {
    add({ role: "system", text: `${approve ? "Подтверждено" : "Отклонено"}: ${item.command}` });
    run(() => (approve ? api.approve(item.id) : api.deny(item.id)));
  }

  return (
    <div className="assistant">
      <div className="messages">
        {messages.length === 0 && <p className="hint">Напишите задачу, например: «создай VLAN 20 с именем USERS».</p>}
        {messages.map((m, i) => (
          <div key={i} className={`message message-${m.role}`}>
            {m.text}
          </div>
        ))}
        {pending.map((p) => (
          <div key={p.id} className={`pending pending-${p.risk}`}>
            <div className="pending-head">
              <span className="badge">{RISK_LABEL[p.risk]}</span>
              <span>Ассистент хочет выполнить команду</span>
            </div>
            <code>{p.command}</code>
            {p.reason && <div className="hint">{p.reason}</div>}
            <div className="actions">
              <button disabled={busy} onClick={() => decide(p, true)}>
                Выполнить
              </button>
              <button className="secondary" disabled={busy} onClick={() => decide(p, false)}>
                Отклонить
              </button>
            </div>
          </div>
        ))}
        {busy && <div className="hint">Ассистент думает…</div>}
        <div ref={end} />
      </div>
      <form className="chat-input" onSubmit={send}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={pending.length ? "Сначала подтвердите или отклоните команду" : "Сообщение ассистенту"}
          disabled={busy || pending.length > 0}
        />
        <button type="submit" disabled={busy || pending.length > 0 || !text.trim()}>
          Отправить
        </button>
      </form>
    </div>
  );
}
