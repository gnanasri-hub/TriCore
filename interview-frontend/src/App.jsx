import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import Chat from './Chat';
import InputBox from './InputBox';
import LiveFeedbackPanel from './LiveFeedbackPanel';
import FeedbackScreen from './FeedbackScreen';
import { Sparkles, Terminal, ArrowRight, Cpu, Zap, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';

axios.defaults.baseURL = import.meta.env.VITE_API_BASE_URL || (
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : "https://tricore-agent-wdjt.onrender.com"
);

const TOPICS = {
  7: "Embeddings",
  8: "Vector Databases",
  9: "Semantic Search",
  10: "Retrieval Engines",
  11: "RAG End-to-End",
  12: "Prompt Engineering",
  13: "Agent Frameworks",
  14: "Agent Tooling",
  15: "LangChain Basics",
  16: "Chatbot Backend",
  17: "Conversation History",
  18: "Token Management",
  19: "Text Summarisation",
  20: "Memory & Context",
  21: "LangChain Agents",
  22: "Multi-Agent Systems",
  23: "Model Context Protocol",
  24: "Agent Planning",
  25: "Evaluation Frameworks",
  26: "LLM Finetuning",
  27: "LoRA & QLoRA",
  28: "Docker & K8s",
  29: "Monitoring & Observability",
  30: "CI/CD for AI Apps",
  31: "Capstone Project",
};

export default function App() {
  // Navigation / Screen states: 'landing' | 'transition' | 'chat' | 'feedback'
  const [screen, setScreen] = useState('landing'); 
  
  // Onboarding Details
  const [name, setName] = useState('Emily Chen');
  const [candId, setCandId] = useState('CAND-003');
  const [role, setRole] = useState('AI Engineer');
  const [sessionId, setSessionId] = useState(`session-${Math.floor(1000 + Math.random() * 9000)}`);
  
  // Validation touch helpers
  const [nameTouched, setNameTouched] = useState(false);
  const [candIdTouched, setCandIdTouched] = useState(false);
  const [roleTouched, setRoleTouched] = useState(false);

  // Transition Step State
  const [transitionStep, setTransitionStep] = useState(0);
  const [tempReply, setTempReply] = useState('');
  const [tempIsFollowUp, setTempIsFollowUp] = useState(false);

  // Active question state
  const [question, setQuestion] = useState("");

  // Adaptive Intelligence & Live states
  const [messages, setMessages] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [sessionStatus, setSessionStatus] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [isFocusMode, setIsFocusMode] = useState(false);
  const [showDifficultyToast, setShowDifficultyToast] = useState(false);
  const [showBasicsToast, setShowBasicsToast] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Dynamically detected domains from answer keywords
  const [detectedDays, setDetectedDays] = useState([]);

  // Pre-interview readiness status
  const [systemStatus, setSystemStatus] = useState('ready');

  const updateSessionStatus = async (sid) => {
    try {
      const resp = await axios.get(`/api/interview/status?sessionId=${sid}`);
      setSessionStatus(resp.data);
    } catch (e) {
      console.error(e);
      setSystemStatus('error');
    }
  };

  // Start form submission triggers transition steps
  const handleStartFormSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !candId.trim() || !role.trim() || !sessionId.trim()) {
      setErrorMsg("All parameters must be set.");
      setNameTouched(true);
      setCandIdTouched(true);
      setRoleTouched(true);
      return;
    }
    
    setErrorMsg('');
    setSystemStatus('loading');
    setScreen('transition');
    setTransitionStep(0);

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
      console.log("API response:", startResp.data);

      const firstQ = startResp.data.reply || startResp.data.question || "Explain REST API design.";
      setTempReply(firstQ);
      setQuestion(firstQ);
      await updateSessionStatus(sessionId.trim());
      setSystemStatus('ready');
    } catch (err) {
      console.error(err);
      console.log("API failed, using fallback.");
      const fallbackQ = "Explain REST API design.";
      setTempReply(fallbackQ);
      setQuestion(fallbackQ);
      // Create a skeleton session status
      setSessionStatus({
        question_count: 1,
        covered_days: [8],
        pending_follow_up: { is_pending: false }
      });
      setSystemStatus('ready');
    }
  };

  // Step-by-step Jarvis loader progression
  useEffect(() => {
    if (screen !== 'transition') return;

    if (transitionStep < 3) {
      const timer = setTimeout(() => {
        setTransitionStep(prev => prev + 1);
      }, 850);
      return () => clearTimeout(timer);
    } else {
      if (!tempReply) return;
      const timer = setTimeout(() => {
        setScreen('chat');
        simulateTyping(tempReply, tempIsFollowUp, "AI Engineering", "Standard");
      }, 700);
      return () => clearTimeout(timer);
    }
  }, [screen, transitionStep, tempReply, tempIsFollowUp]);

  // Generate fallback mock evaluation if API returns null/empty
  const getMockEvaluation = (userMsg) => {
    const wordCount = userMsg.split(/\s+/).filter(w => w.length > 0).length;
    const lower = userMsg.toLowerCase();

    let mockAccuracy = 5;
    let mockDepth = 4;
    let mockClarity = 6;
    let mockStrengths = [];
    let mockGaps = [];

    if (wordCount > 30) {
      mockDepth = 8;
      mockStrengths.push("Detailed structure and context outlining.");
    } else if (wordCount > 12) {
      mockDepth = 6;
      mockStrengths.push("Clear and concise response framework.");
    } else {
      mockDepth = 3;
      mockGaps.push("Response is brief; lacks concrete implementation details.");
    }

    if (lower.includes("vector") || lower.includes("rag") || lower.includes("embedding") || lower.includes("sql") || lower.includes("index") || lower.includes("prompt") || lower.includes("agent")) {
      mockAccuracy = 9;
      mockStrengths.push("Accurate usage of domain terminology keywords.");
    } else {
      mockAccuracy = 5;
      mockGaps.push("Missed referencing semantic components or concrete libraries.");
    }

    if (lower.includes("because") || lower.includes("therefore") || lower.includes("specifically") || lower.includes("such as")) {
      mockClarity = 9;
    } else {
      mockClarity = 6;
    }

    return {
      technical_accuracy: mockAccuracy,
      depth: mockDepth,
      clarity: mockClarity,
      strengths: mockStrengths.length > 0 ? mockStrengths : ["Response parsed successfully."],
      missing_points: mockGaps.length > 0 ? mockGaps : ["No major structural gaps detected."]
    };
  };

  // Advance a turn
  const handleSendMessage = async (userMessage) => {
    setIsFocusMode(false);
    const userMsgObj = { role: 'user', content: userMessage, id: Date.now() };
    setMessages((prev) => [...prev, userMsgObj]);
    setIsThinking(true);

    // Dynamic Domain Keyword Detection
    const lowerMsg = userMessage.toLowerCase();
    const newDetections = [];
    if (lowerMsg.includes("embed") || lowerMsg.includes("sentence-transformer")) newDetections.push(7);
    if (lowerMsg.includes("vector") || lowerMsg.includes("pinecone") || lowerMsg.includes("chroma") || lowerMsg.includes("qdrant")) newDetections.push(8);
    if (lowerMsg.includes("semantic") || lowerMsg.includes("similarity")) newDetections.push(9);
    if (lowerMsg.includes("rag") || lowerMsg.includes("retrieval")) newDetections.push(11);
    if (lowerMsg.includes("prompt") || lowerMsg.includes("chain-of-thought") || lowerMsg.includes("system message")) newDetections.push(12);
    if (lowerMsg.includes("agent") || lowerMsg.includes("multi-agent") || lowerMsg.includes("crewai")) newDetections.push(13);
    if (lowerMsg.includes("langchain")) newDetections.push(15);
    if (lowerMsg.includes("mcp") || lowerMsg.includes("model context")) newDetections.push(23);
    if (lowerMsg.includes("docker") || lowerMsg.includes("kubernetes") || lowerMsg.includes("k8s")) newDetections.push(28);
    if (lowerMsg.includes("monitor") || lowerMsg.includes("observe") || lowerMsg.includes("prometheus")) newDetections.push(29);

    if (newDetections.length > 0) {
      setDetectedDays(prev => {
        const combined = [...prev, ...newDetections];
        return Array.from(new Set(combined));
      });
    }

    try {
      const payload = {
        sessionId: sessionId.trim(),
        message: userMessage
      };

      const turnResp = await axios.post('/api/interview', payload);
      console.log("API response:", turnResp.data);
      const isDone = turnResp.data.done;

      const nextQ = turnResp.data.reply || turnResp.data.question || "Explain REST API design.";
      setQuestion(nextQ);

      // Extract evaluation details or compile mock fallback
      let evalData = turnResp.data.evaluation;
      if (!evalData) {
        evalData = getMockEvaluation(userMessage);
      }
      
      setEvaluation(evalData);
      
      // Trigger difficulty/basics scaling alerts
      let activeDiff = "Standard";
      if (evalData.technical_accuracy >= 8) {
        setShowDifficultyToast(true);
        activeDiff = "Hard";
        setTimeout(() => setShowDifficultyToast(false), 3500);
      } else if (evalData.technical_accuracy <= 5) {
        setShowBasicsToast(true);
        activeDiff = "Easy";
        setTimeout(() => setShowBasicsToast(false), 3500);
      }

      await updateSessionStatus(sessionId.trim());

      if (isDone) {
        setIsThinking(false);
        setScreen('feedback');
        setMessages((prev) => [
          ...prev, 
          { 
            role: 'assistant', 
            content: nextQ, 
            feedback: turnResp.data.feedback, 
            evaluation: evalData,
            id: Date.now() + 1 
          }
        ]);
      } else {
        const statusCheck = await axios.get(`/api/interview/status?sessionId=${sessionId.trim()}`);
        const isFollowUp = statusCheck.data?.pending_follow_up?.is_pending || false;
        
        // Map active topic
        const activeDays = statusCheck.data?.covered_days || [];
        const activeTopic = activeDays.length > 0
          ? (TOPICS[activeDays[activeDays.length - 1]] || "System Design")
          : "AI Engineering";

        simulateTyping(nextQ, isFollowUp, activeTopic, activeDiff, evalData);
      }
    } catch (err) {
      console.error(err);
      console.log("API failed, using fallback.");
      const fallbackQ = "Explain REST API design.";
      setQuestion(fallbackQ);

      const evalData = getMockEvaluation(userMessage);
      setEvaluation(evalData);
      
      // Incremented fallback states
      setSessionStatus(prev => ({
        question_count: (prev?.question_count || 1) + 1,
        covered_days: prev?.covered_days || [8],
        pending_follow_up: { is_pending: false }
      }));

      simulateTyping(fallbackQ, false, "System Design", "Standard", evalData);
    }
  };

  const simulateTyping = (fullText, isFollowUp = false, domain = "AI Engineering", difficulty = "Standard", evaluationPayload = null) => {
    setTimeout(() => {
      setIsThinking(false);

      let currentIdx = 0;
      let typedStr = "";
      const msgId = Date.now() + Math.random();
      setMessages((prev) => [...prev, { 
        role: 'assistant', 
        content: '', 
        isFollowUp, 
        domain,
        difficulty,
        evaluation: evaluationPayload,
        id: msgId 
      }]);
      
      const interval = setInterval(() => {
        if (currentIdx < fullText.length) {
          const chunk = fullText.slice(currentIdx, currentIdx + 2);
          typedStr += chunk;
          currentIdx += 2;
          setMessages((prev) => prev.map((m) => m.id === msgId ? { ...m, content: typedStr } : m));
        } else {
          clearInterval(interval);
          setIsFocusMode(true);
        }
      }, 12);
    }, 2000);
  };

  const handleReset = () => {
    setScreen('landing');
    setMessages([]);
    setQuestion("");
    setSessionStatus(null);
    setEvaluation(null);
    setIsFocusMode(false);
    setShowDifficultyToast(false);
    setShowBasicsToast(false);
    setDetectedDays([]);
    setNameTouched(false);
    setCandIdTouched(false);
    setRoleTouched(false);
    setSessionId(`session-${Math.floor(1000 + Math.random() * 9000)}`);
  };

  // On-the-fly field validation helpers
  const nameValid = name.trim().length > 0;
  const candIdValid = candId.trim().length > 0;
  const roleValid = role.trim().length > 0;

  // Stagger variants for entry preview chips
  const chipContainerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.08, delayChildren: 0.2 }
    }
  };

  const chipItemVariants = {
    hidden: { opacity: 0, y: 10 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 200, damping: 15 } }
  };

  // Maps transition steps to strings
  const getTransitionString = (step) => {
    switch (step) {
      case 0: return "Initializing Evaluation Engine...";
      case 1: return "Loading Candidate Profile...";
      case 2: return "Calibrating Difficulty Model...";
      case 3: return "AI Evaluation Engine Ready";
      default: return "Initializing Engine...";
    }
  };

  const fakeProgressPercent = transitionStep === 0 ? 25 : transitionStep === 1 ? 55 : transitionStep === 2 ? 80 : 100;

  return (
    <div className="min-h-screen relative flex flex-col justify-between overflow-x-hidden font-sans">
      <div className="noise-bg" />
      
      {/* Glow Orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-900/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-900/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Navbar */}
      <header className="w-full max-w-7xl mx-auto px-6 py-5 flex justify-between items-center z-10 border-b border-zinc-900">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-600 to-pink-655 flex items-center justify-center text-white font-bold text-sm shadow-[0_0_15px_rgba(168,85,247,0.4)]">
            T
          </div>
          <span className="font-bold tracking-tight font-display text-[16px]">
            TriCore <span className="text-zinc-500 font-normal">AI Agent</span>
          </span>
        </div>

        <div className="flex items-center gap-4">
          <span className="text-[11px] text-zinc-550 font-mono flex items-center gap-1 bg-zinc-900 px-2.5 py-1 rounded-md border border-zinc-800">
            <Terminal size={12} />
            v1.0.0-stable
          </span>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 flex flex-col items-center justify-center py-4 z-10 w-full">
        <AnimatePresence mode="wait">
          
          {/* LANDING SCREEN */}
          {screen === 'landing' && (
            <motion.div
              key="landing"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.97 }}
              transition={{ duration: 0.35 }}
              className="w-full max-w-md px-4"
            >
              {/* Top status readiness bar */}
              <div className="flex justify-between items-center mb-6 bg-zinc-950/40 border border-zinc-900 px-4 py-2 rounded-xl">
                <span className="text-[10px] font-bold tracking-wider font-mono text-zinc-550 uppercase">System Integrity</span>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full animate-pulse ${
                    systemStatus === 'ready' ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.6)]' : systemStatus === 'loading' ? 'bg-amber-500' : 'bg-red-500'
                  }`} />
                  <span className="text-[10px] font-bold font-mono text-zinc-300">
                    {systemStatus === 'ready' ? 'AI Ready' : systemStatus === 'loading' ? 'Initializing AI...' : 'System Issue'}
                  </span>
                </div>
              </div>

              <div className="text-center mb-8">
                <div className="inline-flex items-center gap-2 bg-purple-500/10 border border-purple-500/20 text-purple-300 px-3.5 py-1 rounded-full text-xs font-semibold mb-4">
                  <Cpu size={12} className="animate-spin text-purple-400" />
                  Technical Evaluation Engine
                </div>
                
                <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight font-display bg-clip-text text-transparent bg-gradient-to-b from-white via-zinc-200 to-zinc-400 mb-3">
                  AI Interview Simulator
                </h1>
                <p className="text-zinc-400 text-sm max-w-sm mx-auto leading-relaxed">
                  Enter parameters to initialize technical grading session.
                </p>
              </div>

              {/* Form Card */}
              <div className="glass-card p-6 rounded-3xl border-zinc-800/80 shadow-[0_10px_40px_rgba(0,0,0,0.4)]">
                <form onSubmit={handleStartFormSubmit} className="space-y-4">
                  
                  {/* Session ID */}
                  <div>
                    <label className="block text-[11px] font-bold text-zinc-500 uppercase tracking-wider mb-1.5 pl-0.5">
                      Session ID
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={sessionId}
                        onChange={(e) => setSessionId(e.target.value)}
                        className="w-full bg-zinc-950/80 border border-zinc-850 focus:border-purple-500/40 focus:ring-2 focus:ring-purple-500/15 rounded-xl px-3.5 py-2.5 text-[14px] text-zinc-200 focus:outline-none transition-all font-mono"
                      />
                    </div>
                    <span className="block text-[9px] text-zinc-500 font-mono mt-1 pl-0.5">
                      Auto-generated session
                    </span>
                  </div>

                  {/* Candidate Name */}
                  <div>
                    <label className="block text-[11px] font-bold text-zinc-550 uppercase tracking-wider mb-1.5 pl-0.5">
                      Candidate Name
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={name}
                        onBlur={() => setNameTouched(true)}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="e.g. Sarah Johnson"
                        className={`w-full bg-zinc-950/80 border rounded-xl px-3.5 py-2.5 text-[14px] text-zinc-200 focus:outline-none transition-all ${
                          nameTouched && !nameValid 
                            ? 'border-red-500/40 focus:border-red-500/60 focus:ring-2 focus:ring-red-500/15' 
                            : nameValid
                              ? 'border-emerald-500/30 focus:border-emerald-500/50 focus:ring-2 focus:ring-emerald-500/15'
                              : 'border-zinc-850 focus:border-purple-500/40 focus:ring-2 focus:ring-purple-500/15'
                        }`}
                      />
                      {nameValid && <CheckCircle2 size={14} className="text-emerald-400 absolute right-3.5 top-1/2 -translate-y-1/2" />}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    {/* Candidate ID */}
                    <div>
                      <label className="block text-[11px] font-bold text-zinc-505 uppercase tracking-wider mb-1.5 pl-0.5">
                        Candidate ID
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          value={candId}
                          onBlur={() => setCandIdTouched(true)}
                          onChange={(e) => setCandId(e.target.value)}
                          placeholder="CAND-001"
                          className={`w-full bg-zinc-950/80 border rounded-xl px-3.5 py-2.5 text-[14px] text-zinc-200 focus:outline-none transition-all font-mono ${
                            candIdTouched && !candIdValid
                              ? 'border-red-500/40 focus:border-red-500/60 focus:ring-2 focus:ring-red-500/15'
                              : candIdValid
                                ? 'border-emerald-500/30 focus:border-emerald-500/50 focus:ring-2 focus:ring-emerald-500/15'
                                : 'border-zinc-850 focus:border-purple-500/40 focus:ring-2 focus:ring-purple-500/15'
                          }`}
                        />
                        {candIdValid && <CheckCircle2 size={14} className="text-emerald-400 absolute right-3.5 top-1/2 -translate-y-1/2" />}
                      </div>
                    </div>

                    {/* Job Role */}
                    <div>
                      <label className="block text-[11px] font-bold text-zinc-505 uppercase tracking-wider mb-1.5 pl-0.5">
                        Job Role
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          value={role}
                          onBlur={() => setRoleTouched(true)}
                          onChange={(e) => setRole(e.target.value)}
                          placeholder="e.g. AI Engineer"
                          className={`w-full bg-zinc-950/80 border rounded-xl px-3.5 py-2.5 text-[14px] text-zinc-200 focus:outline-none transition-all ${
                            roleTouched && !roleValid
                              ? 'border-red-500/40 focus:border-red-500/60 focus:ring-2 focus:ring-red-500/15'
                              : roleValid
                                ? 'border-emerald-500/30 focus:border-emerald-500/50 focus:ring-2 focus:ring-emerald-500/15'
                                : 'border-zinc-850 focus:border-purple-500/40 focus:ring-2 focus:ring-purple-500/15'
                          }`}
                        />
                        {roleValid && <CheckCircle2 size={14} className="text-emerald-400 absolute right-3.5 top-1/2 -translate-y-1/2" />}
                      </div>
                    </div>
                  </div>

                  {errorMsg && <div className="p-3 bg-red-950/20 border border-red-500/20 text-red-400 text-xs rounded-xl text-center">{errorMsg}</div>}

                  <motion.button 
                    type="submit" 
                    whileHover={{ scale: 1.02 }} 
                    whileTap={{ scale: 0.98 }} 
                    className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-semibold py-3.5 rounded-xl cursor-pointer hover:from-purple-500 hover:to-blue-500 transition-all duration-300 mt-2 text-sm shadow-[0_0_15px_rgba(168,85,247,0.25)]"
                  >
                    Start System Calibration 
                    <ArrowRight size={16} />
                  </motion.button>
                </form>
              </div>

              {/* Feature Chips */}
              <div className="mt-8">
                <span className="block text-[10px] font-bold text-zinc-550 uppercase tracking-widest text-center mb-3">Evaluation System Preview</span>
                <motion.div variants={chipContainerVariants} initial="hidden" animate="show" className="flex flex-wrap gap-2 justify-center">
                  <motion.span variants={chipItemVariants} className="text-[10px] font-bold bg-zinc-950 border border-zinc-900 hover:border-purple-500/20 text-zinc-400 px-3 py-1 rounded-full font-mono flex items-center gap-1.5 transition-colors">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse" /> Adaptive Questions
                  </motion.span>
                  <motion.span variants={chipItemVariants} className="text-[10px] font-bold bg-zinc-950 border border-zinc-900 hover:border-purple-500/20 text-zinc-400 px-3 py-1 rounded-full font-mono flex items-center gap-1.5 transition-colors">
                    <span className="w-1.5 h-1.5 rounded-full bg-pink-500 animate-pulse" /> Real-time Feedback
                  </motion.span>
                  <motion.span variants={chipItemVariants} className="text-[10px] font-bold bg-zinc-950 border border-zinc-900 hover:border-purple-500/20 text-zinc-400 px-3 py-1 rounded-full font-mono flex items-center gap-1.5 transition-colors">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" /> Difficulty Scaling
                  </motion.span>
                  <motion.span variants={chipItemVariants} className="text-[10px] font-bold bg-zinc-950 border border-zinc-900 hover:border-purple-500/20 text-zinc-400 px-3 py-1 rounded-full font-mono flex items-center gap-1.5 transition-colors">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> AI Evaluation Mode
                  </motion.span>
                </motion.div>
              </div>
            </motion.div>
          )}

          {/* CINEMATIC AI ACTIVATION OVERLAY */}
          {screen === 'transition' && (
            <motion.div 
              key="transition" 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              exit={{ opacity: 0, scale: 1.05 }} 
              transition={{ duration: 0.4 }}
              className="fixed inset-0 w-screen h-screen flex flex-col items-center justify-center bg-[#020202] z-50 p-6"
            >
              <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[350px] h-[350px] bg-purple-650/10 rounded-full blur-[100px] pointer-events-none" />
              <div className="flex flex-col items-center max-w-md w-full text-center relative z-10">
                <Cpu size={40} className="text-purple-500 animate-spin mb-6" />
                <motion.h2 key={transitionStep} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="text-2xl font-bold font-display text-zinc-100 tracking-tight mb-4 min-h-[36px]">{getTransitionString(transitionStep)}</motion.h2>
                <p className="text-zinc-555 text-xs font-mono mb-8 uppercase tracking-widest animate-pulse">System Calibration In Progress</p>
                <div className="w-64 h-1 bg-zinc-955 border border-zinc-900 rounded-full overflow-hidden mb-8 relative">
                  <motion.div initial={{ width: "0%" }} animate={{ width: `${fakeProgressPercent}%` }} transition={{ duration: 0.7, ease: "easeInOut" }} className="h-full bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 rounded-full relative"><div className="absolute top-0 right-0 bottom-0 left-0 bg-white/20 animate-pulse" /></motion.div>
                </div>
                <div className="w-56 space-y-3.5 text-left font-mono text-xs select-none">
                  <div className="flex items-center gap-3">
                    <div className="shrink-0">{transitionStep > 0 ? <CheckCircle2 size={15} className="text-emerald-400 fill-emerald-950/20" /> : <Loader2 size={14} className="text-purple-400 animate-spin" />}</div>
                    <span className={`font-semibold transition-colors ${transitionStep >= 0 ? 'text-zinc-400 font-bold' : 'text-zinc-700'}`}>Profile Loaded</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="shrink-0">{transitionStep > 1 ? <CheckCircle2 size={15} className="text-emerald-400 fill-emerald-950/20" /> : transitionStep === 1 ? <Loader2 size={14} className="text-purple-400 animate-spin" /> : <div className="w-3.5 h-3.5 rounded-full border border-zinc-800" />}</div>
                    <span className={`font-semibold transition-colors ${transitionStep >= 1 ? 'text-zinc-400 font-bold' : 'text-zinc-700'}`}>Question Engine Configured</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="shrink-0">{transitionStep > 2 ? <CheckCircle2 size={15} className="text-emerald-400 fill-emerald-950/20" /> : transitionStep === 2 ? <Loader2 size={14} className="text-purple-400 animate-spin" /> : <div className="w-3.5 h-3.5 rounded-full border border-zinc-800" />}</div>
                    <span className={`font-semibold transition-colors ${transitionStep >= 2 ? 'text-zinc-400 font-bold' : 'text-zinc-700'}`}>Difficulty Vectors Locked</span>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {screen === 'chat' && (
            <motion.div key="chat" initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} transition={{ type: "spring", stiffness: 180, damping: 18, duration: 0.4 }} className="w-full max-w-6xl mx-auto px-4 flex gap-8 items-start h-[calc(100vh-100px)] overflow-hidden">
              <div className="flex-1 flex flex-col justify-between h-full overflow-hidden">
                <Chat messages={messages} isThinking={isThinking} sessionStatus={sessionStatus} isFocusMode={isFocusMode} setIsFocusMode={setIsFocusMode} detectedDays={detectedDays} />
                <div className="w-full max-w-[800px] mx-auto px-4 mt-2 chat-input relative z-50">
                  <InputBox 
                    onSendMessage={handleSendMessage} 
                    disabled={isThinking} 
                    onStartTyping={() => setIsFocusMode(false)} 
                    lastQuestion={question}
                  />
                </div>
              </div>
              <div className="w-[320px] shrink-0 hidden lg:block border-l border-zinc-900 pl-8 h-full overflow-hidden">
                <LiveFeedbackPanel evaluation={evaluation} sessionStatus={sessionStatus} isThinking={isThinking} />
              </div>
            </motion.div>
          )}

          {screen === 'feedback' && (
            <motion.div key="feedback" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="w-full">
              <FeedbackScreen feedback={messages[messages.length - 1]?.feedback} onReset={handleReset} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <AnimatePresence>
        {showDifficultyToast && (
          <motion.div initial={{ opacity: 0, y: 50, scale: 0.9 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 20, scale: 0.9 }} className="fixed bottom-24 left-1/2 -translate-x-1/2 bg-gradient-to-r from-purple-600 to-pink-655 text-white text-xs font-bold uppercase tracking-widest px-4.5 py-3 rounded-full border border-purple-400/30 shadow-[0_0_20px_rgba(168,85,247,0.5)] flex items-center gap-2 z-50">
            <Zap size={13} className="fill-white animate-bounce" />
            <span>Difficulty Increased (Targeting Senior Tier)</span>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showBasicsToast && (
          <motion.div initial={{ opacity: 0, y: 50, scale: 0.9 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 20, scale: 0.9 }} className="fixed bottom-24 left-1/2 -translate-x-1/2 bg-gradient-to-r from-amber-600 to-red-500 text-white text-xs font-bold uppercase tracking-widest px-4.5 py-3 rounded-full border border-amber-400/30 shadow-[0_0_20px_rgba(245,158,11,0.5)] flex items-center gap-2 z-50">
            <AlertCircle size={13} className="text-white animate-bounce" />
            <span>AI is Probing Basics (Calibrating Scenario Depth)</span>
          </motion.div>
        )}
      </AnimatePresence>

      {screen !== 'chat' && (
        <footer className="w-full max-w-7xl mx-auto px-6 py-2 text-center text-[12px] text-zinc-650 opacity-60 border-t border-zinc-900 z-10">
          &copy; {new Date().getFullYear()} TriCore AI. Powered by Advanced Agentic Coding. All rights reserved.
        </footer>
      )}
    </div>
  );
}
