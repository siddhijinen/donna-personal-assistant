import React, { useState, useEffect, useRef } from 'react';

interface WebSocketMessage {
  status: 'SUCCESS' | 'WAIT_FOR_APPROVAL' | 'COMMITTED';
  agent_response: string;
  logs: string[];
  drafted_reply?: string;
}

export default function ChatInterface() {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [input, setInput] = useState('');
  const [logs, setLogs] = useState<string[]>([]);
  const [response, setResponse] = useState('');
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [password, setPassword] = useState('');
  const [approvalStatus, setApprovalStatus] = useState<'IDLE' | 'PENDING' | 'APPROVED'>('IDLE');
  const logEndRef = useRef<HTMLDivElement>(null);

  // 1. Establish secure WebSocket connection on component mount
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/handshake');

    ws.onopen = () => {
      setLogs((prev) => [...prev, '⚡ [WS] Bi-directional telemetry handshake established.']);
    };

    ws.onmessage = (event) => {
      const data: WebSocketMessage = json.parse(event.data);
      setLogs((prev) => [...prev, ...data.logs]);
      setResponse(data.agent_response);

      if (data.status === 'WAIT_FOR_APPROVAL') {
        setRequiresApproval(true);
        setApprovalStatus('PENDING');
      }
    };

    ws.onclose = () => {
      setLogs((prev) => [...prev, '❌ [WS] Connection terminated by host machine.']);
    };

    setSocket(ws);
    return () => ws.close();
  }, []);

  // Auto-scroll pipeline trace logs
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // 2. Submit initial message over the socket stream
  const handleSendMessage = () => {
    if (!socket || !input.trim()) return;
    setLogs([]);
    setResponse('');
    setRequiresApproval(false);
    setApprovalStatus('IDLE');

    socket.send(json.stringify({ text: input }));
    setInput('');
  };

  // 3. Handle HITL token confirmation
  const handleAuthorizeAction = () => {
    if (password === 'secure123') { // Replace with your internal auth validation token
      setApprovalStatus('APPROVED');
      setRequiresApproval(false);
      setLogs((prev) => [...prev, '✅ [AUTH] Passcode verified. Transaction committed to database.', '🏁 Action sequence marked COMPLETE.']);
      setPassword('');
    } else {
      alert('Invalid security passcode. Action rejected.');
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '2rem auto', padding: '1rem', fontFamily: 'monospace' }}>
      <h2>Donna Strategic Workspace Agent</h2>

      {/* Log Output Console */}
      <div style={{ background: '#1e1e1e', color: '#39ff14', padding: '1rem', borderRadius: '6px', height: '250px', overflowY: 'auto', marginBottom: '1rem' }}>
        <strong>⚙️ PIPELINE LOG TRACE:</strong>
        {logs.map((log, index) => (
          <div key={index} style={{ margin: '4px 0', fontSize: '13px' }}>{log}</div>
        ))}
        <div ref={logEndRef} />
      </div>

      {/* Main Agent Response Display */}
      {response && (
        <div style={{ background: '#f4f4f5', padding: '1rem', borderRadius: '6px', borderLeft: '4px solid #6366f1', marginBottom: '1rem' }}>
          <strong>🤖 Donna Response:</strong>
          <p style={{ margin: '0.5rem 0 0' }}>{response}</p>
        </div>
      )}

      {/* Day 11: Emerald Green HITL Approval Guard Component */}
      {requiresApproval && approvalStatus === 'PENDING' && (
        <div style={{ background: '#ecfdf5', border: '2px solid #10b981', color: '#065f46', padding: '1.25rem', borderRadius: '6px', marginBottom: '1rem' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🔒</span> AUTHORIZE ACTION SEQUENCE REQUIRED
          </h4>
          <p style={{ margin: '0 0 1rem 0', fontSize: '14px' }}>
            Donna has prepared a high-integrity database/calendar payload. Enter security passcode to dispatch execution vector.
          </p>
          <div style={{ display: 'flex', gap: '10px' }}>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{ padding: '8px', border: '1px solid #10b981', borderRadius: '4px', flex: '1' }}
            />
            <button
              onClick={handleAuthorizeAction}
              style={{ background: '#10b981', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
            >
              Confirm Token
            </button>
          </div>
        </div>
      )}

      {/* Input Prompt Controls */}
      <div style={{ display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={input}
          disabled={requiresApproval}
          onChange={(e) => setInput(e.target.value)}
          placeholder={requiresApproval ? "Awaiting clearance token..." : "Log an invoice for $75.00... or Check flights..."}
          style={{ flex: '1', padding: '12px', borderRadius: '6px', border: '1px solid #ccc' }}
          onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
        />
        <button
          onClick={handleSendMessage}
          disabled={requiresApproval}
          style={{ padding: '12px 24px', borderRadius: '6px', background: '#6366f1', color: '#fff', border: 'none', cursor: 'pointer' }}
        >
          Dispatch
        </button>
      </div>
    </div>
  );
}