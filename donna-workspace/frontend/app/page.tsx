"use client";

import React, { useState, useEffect, useRef } from "react";

interface Message {
  id: string;
  sender: "user" | "system";
  text: string;
  pipeline?: string[];
}

interface ToastNotif {
  id: string;
  title: string;
  message: string;
  type: string;
  timestamp: string;
}

interface CalendarEvent {
  title: string;
  time: string;
}

export default function DonnaDashboard() {
  // Auth state
  const [authStatus, setAuthStatus] = useState<"LOADING" | "SETUP_NEEDED" | "LOGIN_NEEDED" | "AUTHENTICATED">("LOADING");
  const [passcode, setPasscode] = useState("");
  const [passcodeConfirm, setPasscodeConfirm] = useState("");
  const [authError, setAuthError] = useState("");

  // Chat state
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [notifSocket, setNotifSocket] = useState<WebSocket | null>(null);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Sensitive Op state
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [sensitivityReason, setSensitivityReason] = useState("");
  const [reauthPasscode, setReauthPasscode] = useState("");
  const [reauthError, setReauthError] = useState("");

  // Notifications state
  const [toasts, setToasts] = useState<ToastNotif[]>([]);
  const [notificationHistory, setNotificationHistory] = useState<ToastNotif[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);

  // Calendar state
  const [calendarAgenda, setCalendarAgenda] = useState<CalendarEvent[]>([]);
  const [isCalendarLoading, setIsCalendarLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 1. Initial Auth Check
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/auth/status");
      const data = await res.json();
      if (!data.has_passcode) {
        setAuthStatus("SETUP_NEEDED");
      } else {
        const token = sessionStorage.getItem("donna_token");
        if (token) {
          setAuthStatus("AUTHENTICATED");
          connectWebSockets();
          fetchCalendarAgenda();
          loadPersistedChat();
        } else {
          setAuthStatus("LOGIN_NEEDED");
        }
      }
    } catch (e) {
      setAuthError("Failed to connect to backend. Please ensure the backend server is running at http://127.0.0.1:8000");
      setAuthStatus("LOGIN_NEEDED");
    }
  };

  // 2. Load and Persist Chat History
  const loadPersistedChat = () => {
    const saved = localStorage.getItem("donna_chat_history");
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse chat history", e);
      }
    } else {
      setMessages([
        { id: "init", sender: "system", text: "Hi, I'm Donna. How can I help you today?" }
      ]);
    }

    const savedNotifs = localStorage.getItem("donna_notification_history");
    if (savedNotifs) {
      try {
        setNotificationHistory(JSON.parse(savedNotifs));
      } catch (e) {
        console.error("Failed to parse notification history", e);
      }
    }
  };

  useEffect(() => {
    if (authStatus === "AUTHENTICATED" && messages.length > 0) {
      localStorage.setItem("donna_chat_history", JSON.stringify(messages));
    }
  }, [messages, authStatus]);

  useEffect(() => {
    if (authStatus === "AUTHENTICATED") {
      localStorage.setItem("donna_notification_history", JSON.stringify(notificationHistory));
    }
  }, [notificationHistory, authStatus]);

  const clearChat = () => {
    setMessages([{ id: "init", sender: "system", text: "Hi, I'm Donna. How can I help you today?" }]);
    localStorage.removeItem("donna_chat_history");
  };

  const clearNotifications = () => {
    setNotificationHistory([]);
    localStorage.removeItem("donna_notification_history");
  };

  // 3. Fetch Calendar Agenda
  const fetchCalendarAgenda = async () => {
    setIsCalendarLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/calendar/agenda");
      if (res.ok) {
        const data = await res.json();
        setCalendarAgenda(data);
      }
    } catch (e) {
      console.error("Failed to fetch calendar agenda", e);
    } finally {
      setIsCalendarLoading(false);
    }
  };

  const handleSetup = async () => {
    if (passcode.length < 6) {
      setAuthError("Passcode must be at least 6 characters.");
      return;
    }
    if (passcode !== passcodeConfirm) {
      setAuthError("Passcodes do not match.");
      return;
    }
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/auth/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ passcode }),
      });
      if (res.ok) {
        setAuthStatus("LOGIN_NEEDED");
        setPasscode("");
        setPasscodeConfirm("");
        setAuthError("");
      } else {
        const err = await res.json();
        setAuthError(err.detail);
      }
    } catch (e) {
      setAuthError("Network error.");
    }
  };

  const handleLogin = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ passcode }),
      });
      if (res.ok) {
        sessionStorage.setItem("donna_token", "active");
        setAuthStatus("AUTHENTICATED");
        connectWebSockets();
        fetchCalendarAgenda();
        loadPersistedChat();
      } else {
        setAuthError("Invalid passcode.");
      }
    } catch (e) {
      setAuthError("Network error.");
    }
  };

  // 4. WebSockets
  const connectWebSockets = () => {
    if (!socket) {
      const ws = new WebSocket("ws://127.0.0.1:8000/ws/handshake");
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setIsLoading(false);
        setMessages((prev) => [
          ...prev,
          { id: Date.now().toString(), sender: "system", text: data.agent_response, pipeline: data.logs }
        ]);
        if (data.requires_approval) {
          setRequiresApproval(true);
          setSensitivityReason(data.sensitivity_reason);
        }
        // Refresh Calendar Widget on successful action completion (in case we added/deleted events)
        if (data.status === "SUCCESS") {
          fetchCalendarAgenda();
        }
      };
      setSocket(ws);
    }

    if (!notifSocket) {
      const nws = new WebSocket("ws://127.0.0.1:8000/ws/notifications");
      nws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const newToast: ToastNotif = { id: Date.now().toString(), ...data };
        
        setToasts((prev) => [newToast, ...prev].slice(0, 3));
        setNotificationHistory((prev) => [newToast, ...prev]);

        // Auto dismiss toast after 8s
        setTimeout(() => {
          setToasts((prev) => prev.filter(t => t.id !== newToast.id));
        }, 8000);

        // Auto-refresh Calendar if a conflict or event alert popped up
        fetchCalendarAgenda();
      };
      setNotifSocket(nws);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || !socket || isLoading) return;
    
    setMessages((prev) => [...prev, { id: Date.now().toString(), sender: "user", text: input }]);
    setIsLoading(true);
    socket.send(JSON.stringify({ text: input }));
    setInput("");
  };

  const handleReauth = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/verify-action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ passcode: reauthPasscode }),
      });
      if (res.ok) {
        setRequiresApproval(false);
        setReauthPasscode("");
        setReauthError("");
        setMessages((prev) => [
          ...prev,
          { id: Date.now().toString(), sender: "system", text: "✅ Action authorized and executed." }
        ]);
        fetchCalendarAgenda();
      } else {
        setReauthError("Incorrect passcode.");
      }
    } catch (e) {
      setReauthError("Network error.");
    }
  };

  const cancelReauth = () => {
    setRequiresApproval(false);
    setReauthPasscode("");
    setReauthError("");
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), sender: "system", text: "❌ Action cancelled by user." }
    ]);
  };

  // Renders
  if (authStatus === "LOADING") return <div className="h-screen bg-apple-bg flex items-center justify-center text-apple-textMuted font-sans">Loading...</div>;

  if (authStatus === "SETUP_NEEDED" || authStatus === "LOGIN_NEEDED") {
    return (
      <div className="h-screen bg-apple-bg flex items-center justify-center text-apple-textMain font-sans">
        <div className="bg-apple-card border border-apple-border p-8 rounded-2xl w-full max-w-sm shadow-2xl flex flex-col items-center">
          <div className="h-12 w-12 rounded-full bg-apple-blue flex items-center justify-center mb-6 shadow-lg">
            <span className="text-2xl">D</span>
          </div>
          <h2 className="text-xl font-semibold mb-2">
            {authStatus === "SETUP_NEEDED" ? "Welcome to Donna" : "Welcome Back"}
          </h2>
          <p className="text-apple-textMuted text-sm mb-6 text-center">
            {authStatus === "SETUP_NEEDED" ? "Create a secure passcode to protect your data." : "Enter your passcode to unlock."}
          </p>
          
          <input
            type="password"
            placeholder="Passcode"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
            className="w-full bg-apple-bg border border-apple-border rounded-lg px-4 py-3 mb-4 focus:outline-none focus:border-apple-blue transition-colors text-center tracking-widest text-lg"
          />
          
          {authStatus === "SETUP_NEEDED" && (
            <input
              type="password"
              placeholder="Confirm Passcode"
              value={passcodeConfirm}
              onChange={(e) => setPasscodeConfirm(e.target.value)}
              className="w-full bg-apple-bg border border-apple-border rounded-lg px-4 py-3 mb-4 focus:outline-none focus:border-apple-blue transition-colors text-center tracking-widest text-lg"
            />
          )}

          {authError && <p className="text-apple-red text-sm mb-4">{authError}</p>}

          <button
            onClick={authStatus === "SETUP_NEEDED" ? handleSetup : handleLogin}
            className="w-full bg-apple-blue hover:bg-blue-500 text-white font-medium py-3 rounded-lg transition-colors"
          >
            {authStatus === "SETUP_NEEDED" ? "Create Passcode" : "Unlock"}
          </button>
        </div>
      </div>
    );
  }

  // Dashboard Render
  return (
    <div className="flex h-screen bg-apple-bg text-apple-textMain font-sans overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-apple-card border-r border-apple-border flex flex-col justify-between p-4">
        <div>
          <div className="flex items-center space-x-3 mb-8 px-2">
            <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-apple-blue to-blue-600 flex items-center justify-center shadow-md">
              <span className="font-bold text-lg">D</span>
            </div>
            <h1 className="text-lg font-semibold tracking-wide">Donna</h1>
            <div className="h-2 w-2 rounded-full bg-apple-green ml-auto"></div>
          </div>
          <nav className="space-y-2">
            <button 
              onClick={() => setShowNotifications(false)}
              className={`w-full text-left px-4 py-2.5 rounded-lg font-medium text-sm transition-colors ${!showNotifications ? 'bg-apple-border/50 text-apple-blue' : 'hover:bg-apple-border/30 text-apple-textMuted'}`}
            >
              Assistant
            </button>
            <button 
              onClick={() => setShowNotifications(true)}
              className={`w-full text-left px-4 py-2.5 rounded-lg font-medium text-sm transition-colors flex items-center justify-between ${showNotifications ? 'bg-apple-border/50 text-apple-blue' : 'hover:bg-apple-border/30 text-apple-textMuted'}`}
            >
              <span>Notifications</span>
              {notificationHistory.length > 0 && (
                <span className="h-5 min-w-[20px] px-1 bg-apple-red text-white text-[10px] rounded-full flex items-center justify-center font-bold">
                  {notificationHistory.length}
                </span>
              )}
            </button>
          </nav>
        </div>
        <div className="space-y-2">
          {showNotifications ? (
            <button 
              onClick={clearNotifications}
              className="w-full bg-apple-card hover:bg-apple-border/50 border border-apple-border text-xs py-2 rounded-lg transition-colors text-apple-textMuted"
            >
              Clear Logs
            </button>
          ) : (
            <button 
              onClick={clearChat}
              className="w-full bg-apple-card hover:bg-apple-border/50 border border-apple-border text-xs py-2 rounded-lg transition-colors text-apple-textMuted"
            >
              Clear Conversation
            </button>
          )}
        </div>
      </aside>

      {/* Main Chat / Notifications View */}
      <main className="flex-1 flex relative overflow-hidden">
        {/* Left Column: Chat or Notification Logs */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Toasts */}
          <div className="absolute top-4 right-6 z-50 flex flex-col gap-3">
            {toasts.map((toast) => (
              <div key={toast.id} className="bg-apple-card border border-apple-border shadow-xl rounded-xl p-4 w-80 apple-blur flex gap-3 animate-fade-in-down">
                <div className={`mt-1 h-2 w-2 rounded-full flex-shrink-0 ${toast.type === 'calendar' ? 'bg-apple-orange' : 'bg-apple-blue'}`} />
                <div>
                  <h4 className="font-semibold text-sm mb-1">{toast.title}</h4>
                  <p className="text-xs text-apple-textMuted leading-relaxed">{toast.message}</p>
                </div>
              </div>
            ))}
          </div>

          {showNotifications ? (
            /* Notification History Center */
            <section className="flex-1 overflow-y-auto p-6 md:p-12 space-y-4">
              <h2 className="text-xl font-semibold mb-6">Notification History</h2>
              {notificationHistory.length === 0 ? (
                <div className="h-64 flex flex-col items-center justify-center text-apple-textMuted text-sm">
                  <span>No notifications logged yet.</span>
                </div>
              ) : (
                notificationHistory.map((notif) => (
                  <div key={notif.id} className="bg-apple-card border border-apple-border rounded-xl p-4 flex gap-4 items-start shadow-sm">
                    <div className={`mt-1.5 h-2 w-2 rounded-full flex-shrink-0 ${notif.type === 'calendar' ? 'bg-apple-orange' : 'bg-apple-blue'}`} />
                    <div className="flex-1">
                      <div className="flex justify-between items-baseline mb-1">
                        <h4 className="font-semibold text-sm">{notif.title}</h4>
                        <span className="text-[10px] text-apple-textMuted font-mono">
                          {new Date(notif.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <p className="text-xs text-apple-textMuted leading-relaxed">{notif.message}</p>
                    </div>
                  </div>
                ))
              )}
            </section>
          ) : (
            /* Chat Interface */
            <>
              <section className="flex-1 overflow-y-auto p-6 md:p-12 space-y-6">
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}>
                    <div
                      className={`max-w-[80%] px-5 py-3.5 rounded-2xl ${
                        msg.sender === "user"
                          ? "bg-apple-blue text-white rounded-tr-sm"
                          : "bg-apple-card border border-apple-border text-apple-textMain rounded-tl-sm shadow-sm"
                      }`}
                    >
                      <div className="whitespace-pre-line text-[15px] leading-relaxed">
                        {msg.text}
                      </div>
                      
                      {msg.pipeline && msg.pipeline.length > 0 && (
                        <details className="mt-3 pt-3 border-t border-apple-border/50 text-xs text-apple-textMuted">
                          <summary className="cursor-pointer hover:text-white transition-colors">Show thought process</summary>
                          <div className="mt-2 space-y-1 font-mono">
                            {msg.pipeline.map((step, idx) => (
                              <div key={idx}>› {step}</div>
                            ))}
                          </div>
                        </details>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </section>

              {/* Input area */}
              <footer className="p-6 bg-apple-bg/80 apple-blur border-t border-apple-border">
                <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex gap-3 relative">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask Donna to schedule a meeting, read emails, or send a payment..."
                    className="flex-1 bg-apple-card border border-apple-border rounded-full pl-6 pr-12 py-4 text-[15px] focus:outline-none focus:border-apple-blue transition-colors shadow-sm"
                    disabled={isLoading || requiresApproval}
                  />
                  <button
                    type="submit"
                    disabled={isLoading || requiresApproval || !input.trim()}
                    className="absolute right-2 top-2 bottom-2 aspect-square rounded-full bg-apple-blue hover:bg-blue-500 flex items-center justify-center transition-colors disabled:opacity-50 disabled:hover:bg-apple-blue"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 text-white ml-0.5">
                      <path d="M3.478 2.404a.75.75 0 00-.926.941l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.404z" />
                    </svg>
                  </button>
                </form>
              </footer>
            </>
          )}
        </div>

        {/* Right Column: Google Calendar Agenda Widget */}
        <aside className="w-80 bg-apple-card border-l border-apple-border flex flex-col p-6 overflow-y-auto">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-semibold text-base tracking-wide">Today's Agenda</h3>
            <button 
              onClick={fetchCalendarAgenda} 
              className="text-apple-blue hover:text-blue-400 text-xs transition-colors"
              disabled={isCalendarLoading}
            >
              {isCalendarLoading ? "Refreshing..." : "Refresh"}
            </button>
          </div>

          <div className="space-y-4">
            {calendarAgenda.length === 0 ? (
              <div className="h-48 border border-dashed border-apple-border rounded-2xl flex flex-col items-center justify-center p-4 text-center text-apple-textMuted text-xs">
                <span>No calendar events found for today.</span>
                <span className="mt-1">Try scheduling a meeting!</span>
              </div>
            ) : (
              calendarAgenda.map((event, idx) => (
                <div key={idx} className="bg-apple-bg border border-apple-border rounded-xl p-4 hover:border-apple-blue/50 transition-colors shadow-sm">
                  <h4 className="font-semibold text-sm mb-1 line-clamp-2">{event.title}</h4>
                  <div className="text-xs text-apple-textMuted flex items-center space-x-1.5">
                    <span>🕒</span>
                    <span>{event.time}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </aside>

        {/* Re-Auth Modal */}
        {requiresApproval && (
          <div className="absolute inset-0 bg-black/60 apple-blur flex items-center justify-center z-50">
            <div className="bg-apple-card border border-apple-border w-full max-w-md p-8 rounded-3xl shadow-2xl animate-fade-in-up flex flex-col items-center text-center">
              <div className="h-12 w-12 rounded-full bg-apple-orange/20 flex items-center justify-center mb-4">
                <span className="text-2xl">🔒</span>
              </div>
              <h3 className="text-lg font-semibold mb-2">Authentication Required</h3>
              <p className="text-apple-textMuted text-sm mb-6 leading-relaxed">
                {sensitivityReason}
              </p>
              
              <input
                type="password"
                value={reauthPasscode}
                onChange={(e) => setReauthPasscode(e.target.value)}
                placeholder="Passcode"
                className="w-full bg-apple-bg border border-apple-border rounded-xl px-4 py-3 mb-2 text-center tracking-widest text-lg focus:outline-none focus:border-apple-orange transition-colors"
              />
              
              {reauthError && <p className="text-apple-red text-sm mb-2">{reauthError}</p>}
              
              <div className="flex w-full gap-3 mt-4">
                <button
                  onClick={cancelReauth}
                  className="flex-1 px-4 py-3 bg-apple-border/50 hover:bg-apple-border text-white rounded-xl transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={handleReauth}
                  className="flex-1 px-4 py-3 bg-apple-orange hover:bg-orange-500 text-white rounded-xl transition-colors font-medium"
                >
                  Authorize
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}