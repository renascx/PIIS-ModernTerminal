import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import { useEffect, useRef, useState } from "react";

import { terminalUrl } from "../api";

type Props = { sessionId: string };

export default function TerminalView({ sessionId }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"connecting" | "open" | "closed">("connecting");

  useEffect(() => {
    const term = new Terminal({ cursorBlink: true, fontSize: 14, convertEol: true });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(container.current!);
    fit.fit();

    const socket = new WebSocket(terminalUrl(sessionId));
    socket.onopen = () => setStatus("open");
    socket.onclose = () => setStatus("closed");
    socket.onmessage = (event) => term.write(String(event.data));
    const input = term.onData((data) => {
      if (socket.readyState === WebSocket.OPEN) socket.send(data);
    });

    const onResize = () => fit.fit();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      input.dispose();
      socket.close();
      term.dispose();
    };
  }, [sessionId]);

  return (
    <div className="terminal-wrap">
      <div className={`status status-${status}`}>
        {status === "connecting" && "Подключение к терминалу…"}
        {status === "open" && "Терминал подключён"}
        {status === "closed" && "Соединение с терминалом закрыто"}
      </div>
      <div className="terminal" ref={container} />
    </div>
  );
}
