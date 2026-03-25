import { useState, useEffect, useRef, useCallback } from "react";
import {
  sendChatMessage,
  fetchChatHistory,
  clearChat,
  fetchChatWelcome,
  type ChatMessage,
} from "../api/daedalusClient";
import "./DaedalusChatPanel.css";

const SUGGESTIONS = [
  "What's the current status?",
  "How is alignment?",
  "Who am I?",
  "Show fleet health",
  "Any incidents?",
  "Help",
];

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function isPreformatted(content: string): boolean {
  return content.includes("\n") && (content.includes("  ") || content.includes(":"));
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const roleClass = `chat-msg chat-msg--${msg.role}`;
  const pre = msg.role === "daedalus" && isPreformatted(msg.content);

  return (
    <div className={roleClass}>
      <div className="chat-bubble">
        {pre ? <pre>{msg.content}</pre> : msg.content}
      </div>
      <span className="chat-msg__time">{formatTime(msg.timestamp)}</span>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="chat-typing">
      <span className="chat-typing__dot" />
      <span className="chat-typing__dot" />
      <span className="chat-typing__dot" />
      <span className="chat-typing__label">Daedalus is thinking…</span>
    </div>
  );
}

export function DaedalusChatPanel() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    if (!open || initialized) return;
    let cancelled = false;

    (async () => {
      try {
        const history = await fetchChatHistory();
        if (cancelled) return;
        if (history.length > 0) {
          setMessages(history);
        } else {
          const welcome = await fetchChatWelcome();
          if (cancelled) return;
          setMessages([welcome]);
        }
        setInitialized(true);
      } catch {
        if (cancelled) return;
        try {
          const welcome = await fetchChatWelcome();
          if (!cancelled) {
            setMessages([welcome]);
            setInitialized(true);
          }
        } catch {
          setInitialized(true);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [open, initialized]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [open]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || sending) return;

    const optimistic: ChatMessage = {
      id: `opt-${Date.now()}`,
      role: "operator",
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimistic]);
    setInput("");
    setSending(true);

    try {
      const { userMessage, daedalusMessage } = await sendChatMessage(text);
      setMessages((prev) => {
        const without = prev.filter((m) => m.id !== optimistic.id);
        return [...without, userMessage, daedalusMessage];
      });
    } catch (err) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        role: "system",
        content: `Failed to send message. ${err instanceof Error ? err.message : ""}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setSending(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [input, sending]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleSuggestion = useCallback(
    (text: string) => {
      setInput(text);
      setTimeout(() => inputRef.current?.focus(), 50);
    },
    [],
  );

  const handleClear = useCallback(async () => {
    try {
      await clearChat();
      setMessages([]);
      setInitialized(false);
    } catch { /* ignore */ }
  }, []);

  const handleTextareaInput = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setInput(e.target.value);
      const el = e.target;
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 120) + "px";
    },
    [],
  );

  const showSuggestions = messages.length <= 1 && !sending;

  return (
    <>
      {/* Floating toggle */}
      <button
        className={`chat-toggle${open ? " is-open" : ""}`}
        onClick={() => setOpen((o) => !o)}
        title={open ? "Close chat" : "Talk to Daedalus"}
        aria-label={open ? "Close chat" : "Open chat"}
      >
        {open ? "\u2715" : "\u2731"}
        {!open && <span className="chat-toggle__badge" />}
      </button>

      {/* Chat window */}
      {open && (
        <div className="chat-window" role="dialog" aria-label="Chat with Daedalus">
          {/* Header */}
          <div className="chat-header">
            <div className="chat-header__avatar">{"\u2666"}</div>
            <div className="chat-header__info">
              <div className="chat-header__name">Daedalus</div>
              <div className="chat-header__status">
                <span className="chat-header__dot" />
                <span>Online</span>
              </div>
            </div>
            <div className="chat-header__actions">
              <button
                className="chat-header__btn"
                onClick={handleClear}
                title="Clear conversation"
                aria-label="Clear conversation"
              >
                {"\u2672"}
              </button>
              <button
                className="chat-header__btn"
                onClick={() => setOpen(false)}
                title="Close"
                aria-label="Close chat"
              >
                {"\u2212"}
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="chat-messages">
            {messages.length === 0 && !sending && (
              <div className="chat-empty">
                <span className="chat-empty__icon">{"\u2666"}</span>
                <span className="chat-empty__text">
                  Ask Daedalus about system status, alignment, trust, nodes, or governance.
                </span>
                <span className="chat-empty__hint">
                  Press Enter to send, Shift+Enter for new line.
                </span>
              </div>
            )}
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            {sending && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggestion pills */}
          {showSuggestions && (
            <div className="chat-suggestions">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="chat-suggestion"
                  onClick={() => handleSuggestion(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="chat-input-area">
            <div className="chat-input-row">
              <textarea
                ref={inputRef}
                className="chat-input"
                value={input}
                onChange={handleTextareaInput}
                onKeyDown={handleKeyDown}
                placeholder="Talk to Daedalus…"
                rows={1}
                disabled={sending}
                aria-label="Message input"
              />
              <button
                className="chat-send"
                onClick={handleSend}
                disabled={!input.trim() || sending}
                title="Send message"
                aria-label="Send message"
              >
                {"\u2191"}
              </button>
            </div>
            <div className="chat-input-hint">
              Enter to send &middot; Shift+Enter for new line
            </div>
          </div>
        </div>
      )}
    </>
  );
}
