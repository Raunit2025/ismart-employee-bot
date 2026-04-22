import { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [employeeId, setEmployeeId] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [language, setLanguage] = useState('eng_Latn');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [tickets, setTickets] = useState([]);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(() => { scrollToBottom(); }, [messages, isLoading]);

  const fetchTickets = async (empId) => {
    try {
      const response = await fetch(`http://localhost:8000/tickets/${empId}`);
      const data = await response.json();
      setTickets(data.tickets || []);
    } catch (error) {
      console.error("Error fetching tickets:", error);
    }
  };

  const handleLogin = (e) => {
    e.preventDefault();
    if (employeeId.trim()) {
      setIsLoggedIn(true);
      fetchTickets(employeeId);
    }
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = { sender: 'user', text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: input, 
          employee_id: employeeId,
          language: language 
        })
      });
      const data = await response.json();
      setMessages((prev) => [...prev, { sender: 'bot', text: data.reply }]);
      
      fetchTickets(employeeId); 
    // eslint-disable-next-line no-unused-vars
    } catch (error) {
      setMessages((prev) => [...prev, { sender: 'bot', text: "Error connecting to server." }]);
    }
    
    setIsLoading(false);
  };

  if (!isLoggedIn) {
    return (
      <div className="login-container">
        <div className="login-card">
          <div className="brand-logo">🛡️</div>
          <h2>iSmart Support</h2>
          <p className="subtitle">Employee Assistance Portal</p>
          <form onSubmit={handleLogin}>
            <div className="input-group">
              <label>Employee ID</label>
              <input 
                type="text" 
                placeholder="e.g. EMP101" 
                value={employeeId} 
                onChange={(e) => setEmployeeId(e.target.value)} 
                required
              />
            </div>
            <div className="input-group">
              <label>Preferred Language</label>
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="eng_Latn">English</option>
                <option value="hin_Deva">Hindi (हिंदी)</option>
                <option value="mar_Deva">Marathi (मराठी)</option>
                <option value="ben_Beng">Bengali (বাংলা)</option>                
                <option value="tam_Taml">Tamil (தமிழ்)</option>
                <option value="tel_Telu">Telugu (తెలుగు)</option>
                <option value="kan_Knda">Kannada (ಕನ್ನಡ)</option>
                <option value="guj_Gujr">Gujarati (ગુજરાતી)</option>
                <option value="pan_Guru">Punjabi (ਪੰਜਾਬੀ)</option>
                <option value="ory_Orya">Odia (ଓଡ଼ିଆ)</option>
                <option value="mal_Mlym">Malayalam (മലയാളം)</option>
              </select>
            </div>
            <button type="submit" className="primary-btn">Secure Login</button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout">
      <div className="sidebar">
        <div className="sidebar-header">
          <h3>My Tickets</h3>
        </div>
        <div className="ticket-list">
          {tickets.length === 0 ? (
            <p className="no-tickets">No open tickets.</p>
          ) : (
            tickets.map((ticket) => (
              <div key={ticket.id} className="ticket-card">
                <div className="ticket-header">
                  <span className="ticket-id">#{ticket.id}</span>
                  <span className={`ticket-status ${ticket.status.toLowerCase()}`}>{ticket.status}</span>
                </div>
                <div className="ticket-category">{ticket.category}</div>
                <div className="ticket-meta">
                  <span className={`priority-dot ${ticket.priority.toLowerCase()}`}></span>
                  {ticket.priority} Priority • {ticket.date.split(' ')[0]}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="chat-container">
        <div className="chat-header">
          <div className="header-info">
            <h3>iSmart Assistant</h3>
            <span className="status-indicator">● Online</span>
          </div>
          <div className="user-badge">ID: {employeeId}</div>
        </div>
        
        <div className="chat-history">
          {messages.length === 0 && (
            <div className="empty-state">
              <p>Hello! I am your iSmart Support Assistant.</p>
              <p>How can I help you today?</p>
            </div>
          )}
          {messages.map((msg, idx) => (
            <div key={idx} className={`message-wrapper ${msg.sender}`}>
              <div className={`message ${msg.sender}`}>
                {msg.text.split('\n').map((line, i) => (
                  <span key={i}>{line}<br/></span>
                ))}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message-wrapper bot">
              <div className="message bot typing">
                <div className="dot"></div>
                <div className="dot"></div>
                <div className="dot"></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area">
          <input 
            value={input} 
            onChange={(e) => setInput(e.target.value)} 
            onKeyDown={(e) => { if (e.key === 'Enter') sendMessage(); }}
            placeholder="Type your message here..." 
            autoFocus
          />
          <button onClick={sendMessage} disabled={isLoading || !input.trim()} className="send-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;