import React, { useState, useEffect, useRef } from 'react';

const Chat = () => {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const websocket = useRef(null);

    useEffect(() => {
        // Fetch the token from the backend
        const fetchToken = async () => {
            try {
                const response = await fetch('/chat');
                const data = await response.json();
                const token = data.token;
                
                // Establish WebSocket connection
                websocket.current = new WebSocket(`ws://localhost:8000/ws?token=${token}`);

                websocket.current.onopen = () => {
                    console.log('WebSocket connected');
                };

                websocket.current.onmessage = (event) => {
                    const message = JSON.parse(event.data);
                    setMessages((prevMessages) => [...prevMessages, message]);
                };

                websocket.current.onclose = (event) => {
                    console.log('WebSocket disconnected:', event.code, event.reason);
                };

                websocket.current.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };

                // Clean up the WebSocket connection on component unmount
                return () => {
                    if (websocket.current) {
                        websocket.current.close();
                    }
                };
            } catch (error) {
                console.error('Error fetching token or connecting to WebSocket:', error);
            }
        };

        fetchToken();
    }, []);

    const sendMessage = () => {
        if (inputValue.trim() !== '' && websocket.current && websocket.current.readyState === WebSocket.OPEN) {
            const message = { text: inputValue, sender: 'user' };
            websocket.current.send(JSON.stringify(message));
            setMessages((prevMessages) => [...prevMessages, message]);
            setInputValue('');
        }
    };

    return (
        <div className="chat-container">
            <div className="chat-messages">
                {messages.map((message, index) => (
                    <div key={index} className={`message ${message.sender}`}>
                        {message.text}
                    </div>
                ))}
            </div>
            <div className="chat-input">
                <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Type your message..."
                />
                <button onClick={sendMessage}>Send</button>
            </div>
        </div>
    );
};

export default Chat;