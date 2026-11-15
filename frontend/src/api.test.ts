import { describe, expect, it } from "vitest";

import { errorMessage, terminalUrl } from "./api";

describe("errorMessage", () => {
  it("берёт строку из detail", () => {
    expect(errorMessage({ detail: "Сессия не найдена" }, "x")).toBe("Сессия не найдена");
  });

  it("берёт message из объекта", () => {
    const body = { detail: { message: "Требуется подтверждение", risk: "config" } };
    expect(errorMessage(body, "x")).toBe("Требуется подтверждение");
  });

  it("склеивает ошибки валидации", () => {
    const body = { detail: [{ msg: "поле host обязательно" }, { msg: "плохой порт" }] };
    expect(errorMessage(body, "x")).toBe("поле host обязательно; плохой порт");
  });

  it("возвращает запасной текст", () => {
    expect(errorMessage(null, "Ошибка 500")).toBe("Ошибка 500");
    expect(errorMessage({}, "Ошибка 500")).toBe("Ошибка 500");
  });
});

describe("terminalUrl", () => {
  it("выбирает ws для http и wss для https", () => {
    expect(terminalUrl("abc", { protocol: "http:", host: "localhost:5173" })).toBe(
      "ws://localhost:5173/api/sessions/abc/terminal",
    );
    expect(terminalUrl("abc", { protocol: "https:", host: "example.org" })).toBe(
      "wss://example.org/api/sessions/abc/terminal",
    );
  });
});
