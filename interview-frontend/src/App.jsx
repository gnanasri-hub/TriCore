import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import Chat from './Chat';
import InputBox from './InputBox';
import FeedbackScreen from './FeedbackScreen';
import { Sparkles, Terminal, ArrowRight, Play, Cpu, CheckCircle } from 'lucide-react';

axios.defaults.baseURL = "http://127.0.0.1:8000";

export default function App() {
  // Navigation / State
  const [screen, setScreen] = useState('landing'); // 'landing' | 'chat' | 'feedback'
  
  // Onboarding Form Details
  const [name, setName] = useState('Emily Chen');
  const [candId, setCandId] = useState('CAND-003');
  const [role, setRole] = useState('AI Engineer');
  const [sessionId, setSessionId] = useState(`session-${Math.floor(1000 + Math.random() * 9000)}`);
  
  // Chat state
  const [messages, setMessages] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [sessionStatus, setSessionStatus] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  // Fetch status details from backend
  const updateSessionStatus = async (sid) => {
    try {
      const resp = await axios.get(`/api/interview/status?sessionId=${sid}`);
      setSessionStatus(resp.data);
    } catch (e) {
      console.error("Failed to fetch session status", e);
    }
  };

  // Start interview request
  const handleStartInterview = async (e) => {
    e.preventDefault();
    if (!name.trim() || !candId.trim() || !role.trim() || !sessionId.trim()) {
      setErrorMsg("All fields are required to start.");
      return;
    }
    
    setErrorMsg('');
    setIsThinking(true);
    setScreen('chat');

    try {
      const payload = {
        sessionId: sessionId.trim(),
        candidate: {
          id: candId.trim(),
          name: name.trim(),
          role: role.trim()
        }
      };

      const startResp = await axios.post('/api/interview', payload);
      
      // Simulate typing speed for the opening question
      simulateTyping(startResp.data.reply);
      await updateSessionStatus(sessionId.trim());
    } catch (err) {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || "Failed to start the interview session.");
      setScreen('landing');
      setIsThinking(false);
    }
  };

  // Advance a turn
  const handleSendMessage = async (userMessage) => {
    // Add user message immediately to the screen
    const userMsgObj = { role: 'user', content: userMessage, id: Date.now() };
    setMessages((prev) => [...prev, userMsgObj]);
    setIsThinking(true);

    try {
      const payload = {
        sessionId: sessionId.trim(),
        message: userMessage
      };

      const turnResp = await axios.post('/api/interview', payload);
      const isDone = turnResp.data.done;
      
      // Check if follow-up is pending in the background status
      await updateSessionStatus(sessionId.trim());

      if (isDone) {
        // Stop thinking state and transition to final feedback screen
        setIsThinking(false);
        setScreen('feedback');
        setMessages((prev) => [
          ...prev, 
          { 
            role: 'assistant', 
            content: turnResp.data.reply, 
            feedback: turnResp.data.feedback, 
            id: Date.now() + 1 
          }
        ]);
      } else {
        // Check if follow-up question badge is needed by retrieving current state
        const statusCheck = await axios.get(`/api/interview/status?sessionId=${sessionId.trim()}`);
        const isFollowUp = statusCheck.data?.pending_follow_up?.is_pending || false;
        
        simulateTyping(turnResp.data.reply, isFollowUp);
      }
    } catch (err) {
      console.error(err);
      const errMsg = err.response?.data?.detail || "Failed to submit response.";
      setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${errMsg}. Please try again.` }]);
      setIsThinking(false);
    }
  };

  // Helper to type out response incrementally
  const simulateTyping = (fullText, isFollowUp = false) => {
    let currentIdx = 0;
    let typedStr = "";
    
    // Add a placeholder message block first
    const msgId = Date.now() + Math.random();
    setMessages((prev) => [...prev, { role: 'assistant', content: '', isFollowUp, id: msgId }]);
    
    setIsThinking(false); // turn off thinking dots

    const interval = setInterval(() => {
      if (currentIdx < fullText.length) {
        // Grab next 2 characters for snappy typing feel
        const chunk = fullText.slice(currentIdx, currentIdx + 2);
        typedStr += chunk;
        currentIdx += 2;
        
        setMessages((prev) => 
          prev.map((m) => m.id === msgId ? { ...m, content: typedStr } : m)
        );
      } else {
        clearInterval(interval);
      }
    }, 15);
  };

  const handleReset = () => {
    setScreen('landing');
    setMessages([]);
    setSessionStatus(null);
    setSessionId(`session-${Math.floor(1000 + Math.random() * 9000)}`);
  };

  return (
    <div className="min-h-screen relative flex flex-col justify-between overflow-x-hidden font-sans">
      <div className="noise-bg" />
      
      {/* Glow Orbs in background */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-900/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-900/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Navbar */}
      <header className="w-full max-w-7xl mx-auto px-6 py-5 flex justify-between items-center z-10 border-b border-zinc-900">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-600 to-pink-600 flex items-center justify-center text-white font-bold text-sm shadow-[0_0_15px_rgba(168,85,247,0.4)]">
            T
          </div>
          <span className="font-bold tracking-tight font-display text-[16px]">
            TriCore <span className="text-zinc-500 font-normal">AI Agent</span>
          </span>
        </div>

        <div className="flex items-center gap-4">
          <span className="text-[11px] text-zinc-500 font-mono flex items-center gap-1 bg-zinc-900 px-2.5 py-1 rounded-md border border-zinc-800">
            <Terminal size={12} />
            v1.0.0-stable
          </span>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 flex flex-col items-center justify-center py-8 z-10">
        <AnimatePresence mode="wait">
          
          {/* LANDING SCREEN */}
          {screen === 'landing' && (
            <motion.div
              key="landing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
              className="w-full max-w-md px-4"
            >
              <div className="text-center mb-8">
                <motion.div 
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.2 }}
                  className="inline-flex items-center gap-2 bg-purple-500/10 border border-purple-500/20 text-purple-300 px-3.5 py-1 rounded-full text-xs font-semibold mb-4 shadow-[0_0_15px_rgba(168,85,247,0.1)]"
                >
                  <Cpu size={12} className="animate-spin" />
                  TriCore Cohort Simulator
                </motion.div>
                
                <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight font-display bg-clip-text text-transparent bg-gradient-to-b from-white via-zinc-200 to-zinc-400 mb-3">
                  AI Interview Simulator
                </h1>
                <p className="text-zinc-400 text-sm max-w-sm mx-auto leading-relaxed">
                  Practice real technical interviews based on your TriCore cohort history. Highly personalized, strict grading.
                </p>
              </div>

              {/* Start Form Card */}
              <div className="glass-card p-6 rounded-2xl border-zinc-800">
                <form onSubmit={handleStartInterview} className="space-y-4">
                  <div>
                    <label className="block text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5 pl-0.5">
                      Session ID
                    </label>
                    <input
                      type="text"
                      value={sessionId}
                      onChange={(e) => setSessionId(e.target.value)}
                      className="w-full bg-zinc-950/80 border border-zinc-850 rounded-xl px-3.5 py-2.5 text-[14px] text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-purple-500/30 transition-all font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5 pl-0.5">
                      Candidate Name
                    </label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Sarah Johnson"
                      className="w-full bg-zinc-950/80 border border-zinc-850 rounded-xl px-3.5 py-2.5 text-[14px] text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-purple-500/30 transition-all"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5 pl-0.5">
                        Candidate ID
                      </label>
                      <input
                        type="text"
                        value={candId}
                        onChange={(e) => setCandId(e.target.value)}
                        placeholder="e.g. CAND-001"
                        className="w-full bg-zinc-950/80 border border-zinc-850 rounded-xl px-3.5 py-2.5 text-[14px] text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-purple-500/30 transition-all font-mono"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5 pl-0.5">
                        Job Role
                      </label>
                      <input
                        type="text"
                        value={role}
                        onChange={(e) => setRole(e.target.value)}
                        placeholder="e.g. AI Engineer"
                        className="w-full bg-zinc-950/80 border border-zinc-850 rounded-xl px-3.5 py-2.5 text-[14px] text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-purple-500/30 transition-all"
                      />
                    </div>
                  </div>

                  {errorMsg && (
                    <div className="p-3 bg-red-950/20 border border-red-500/20 text-red-400 text-xs rounded-xl text-center font-medium">
                      {errorMsg}
                    </div>
                  )}

                  <motion.button
                    type="submit"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-purple-600 to-pink-650 hover:from-purple-500 hover:to-pink-550 text-white font-semibold py-3.5 rounded-xl glow-btn-purple cursor-pointer transition-all duration-300 mt-2 text-sm"
                  >
                    Start Technical Interview
                    <ArrowRight size={16} />
                  </motion.button>
                </form>
              </div>
            </motion.div>
          )}

          {/* CHAT SCREEN */}
          {screen === 'chat' && (
            <motion.div
              key="chat"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="w-full h-[calc(100vh-170px)] flex flex-col justify-between"
            >
              {/* Central Chat Stream */}
              <Chat 
                messages={messages} 
                isThinking={isThinking} 
                sessionStatus={sessionStatus}
              />
              
              {/* Bottom Sticky Input Container */}
              <div className="w-full max-w-[800px] mx-auto px-4 mt-2">
                <InputBox 
                  onSendMessage={handleSendMessage} 
                  disabled={isThinking} 
                />
              </div>
            </motion.div>
          )}

          {/* FINAL ASSESSMENT / FEEDBACK SCREEN */}
          {screen === 'feedback' && (
            <motion.div
              key="feedback"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="w-full"
            >
              <FeedbackScreen 
                feedback={messages[messages.length - 1]?.feedback} 
                onReset={handleReset}
              />
            </motion.div>
          )}

        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-7xl mx-auto px-6 py-5 text-center text-xs text-zinc-600 border-t border-zinc-900 z-10">
        &copy; {new Date().getFullYear()} TriCore AI. Powered by Advanced Agentic Coding. All rights reserved.
      </footer>
    </div>
  );
}
