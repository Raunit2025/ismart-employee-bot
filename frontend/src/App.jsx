import { useState } from 'react';
import './App.css';

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;
    
    const newMessages = [...messages, { sender: 'employee', text: input }];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: input }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setMessages([...newMessages, { sender: 'bot', text: data.reply }]);
      
    } catch (error) {
      console.error("Fetch error:", error);
      setMessages([...newMessages, { sender: 'bot', text: "Connection error. Please try again." }]);
    }
    
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: '500px', margin: 'auto', padding: '20px', fontFamily: 'sans-serif' }}>
      <div style={{ backgroundColor: '#0056b3', color: 'white', padding: '15px', borderRadius: '8px 8px 0 0' }}>
        <h2>iSmart Support Chat</h2>
      </div>
      
      <div style={{ height: '400px', overflowY: 'auto', border: '1px solid #ccc', padding: '10px', backgroundColor: '#f9f9f9' }}>
        {messages.map((msg, idx) => (
          <div key={idx} style={{ textAlign: msg.sender === 'employee' ? 'right' : 'left', margin: '10px 0' }}>
            <div style={{ 
              display: 'inline-block', 
              padding: '10px', 
              borderRadius: '8px',
              backgroundColor: msg.sender === 'employee' ? '#d1e7dd' : '#e2e3e5',
              whiteSpace: 'pre-line' 
            }}>
              {msg.text}
            </div>
          </div>
        ))}
        {loading && <div style={{ textAlign: 'left', color: 'gray' }}>Thinking...</div>}
      </div>

      <div style={{ display: 'flex', marginTop: '10px' }}>
        <input 
          style={{ flex: 1, padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
          value={input} 
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Type your issue..." 
        />
        <button onClick={sendMessage} style={{ padding: '10px 20px', marginLeft: '5px', cursor: 'pointer' }}>
          Send
        </button>
      </div>
    </div>
  );
}

export default App;