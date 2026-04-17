"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  FileText, Upload, Copy, Download, Check,
  Zap, Eye, Brain, CreditCard, FileCheck, Shield, Building2,
  Landmark, ClipboardList, Heart, HelpCircle, Menu, X, ArrowRight,
  File, ImageIcon, Clock, Sparkles, BookOpen, Code2,
  AlertCircle, ChevronDown, Share2
} from "lucide-react";

// ─── COLORS ──────────────────────────────────────────────────
const CYAN = "#00d4ff";
const PURPLE = "#a855f7";
const GREEN = "#00ff88";

const DOC_TYPE_COLORS = {
  INVOICE: CYAN, RECEIPT: GREEN, CONTRACT: PURPLE,
  "ID CARD": "#f97316", "BANK STATEMENT": "#3b82f6",
  CHECK: "#eab308", UNKNOWN: "#6b7280",
};

const DOC_TYPES = [
  { name: "Invoice", icon: FileText, desc: "Bills, purchase orders & vendor invoices" },
  { name: "Receipt", icon: CreditCard, desc: "POS receipts, payment confirmations" },
  { name: "Contract", icon: FileCheck, desc: "Legal agreements, NDAs, SOWs" },
  { name: "ID Card", icon: Shield, desc: "Passports, driver licenses, national IDs" },
  { name: "Bank Statement", icon: Building2, desc: "Monthly statements, transaction logs" },
  { name: "W-2 / Tax Form", icon: Landmark, desc: "Tax returns, W-2s, 1099s" },
  { name: "Check", icon: ClipboardList, desc: "Personal & business checks" },
  { name: "Medical Record", icon: Heart, desc: "Lab results, prescriptions, records" },
  { name: "Custom Document", icon: HelpCircle, desc: "Any document — we'll figure it out" },
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function formatJSON(obj) { return JSON.stringify(obj, null, 2); }

// ─── PARTICLES ───────────────────────────────────────────────
function Particles() {
  const particles = Array.from({ length: 24 }, (_, i) => ({
    id: i, x: Math.random() * 100, y: Math.random() * 100,
    delay: Math.random() * 8, dur: 6 + Math.random() * 6,
    size: Math.random() > 0.5 ? "+" : "·",
  }));
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden>
      {particles.map((p) => (
        <span key={p.id} className="absolute text-white/[0.06] select-none"
          style={{ left: `${p.x}%`, top: `${p.y}%`, fontSize: p.size === "+" ? "24px" : "32px",
            fontWeight: 300, animation: `particleFade ${p.dur}s ${p.delay}s ease-in-out infinite` }}>
          {p.size}
        </span>
      ))}
    </div>
  );
}

function ConfidenceBar({ label, value, color = CYAN }) {
  const [w, setW] = useState(0);
  useEffect(() => { const t = setTimeout(() => setW(value * 100), 200); return () => clearTimeout(t); }, [value]);
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-[#888] w-28 shrink-0">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-[#1a1a1a] overflow-hidden">
        <div className="h-full rounded-full transition-all duration-1000 ease-out" style={{ width: `${w}%`, background: color }} />
      </div>
      <span className="text-sm font-mono text-white w-12 text-right">{Math.round(value * 100)}%</span>
    </div>
  );
}

function FieldCard({ label, value, delay = 0 }) {
  return (
    <div className="bg-[#111] border border-[#2a2a2a] rounded-xl p-4 opacity-0"
      style={{ animation: `cardIn 0.5s ${delay}ms ease-out forwards` }}>
      <p className="text-xs text-[#666] uppercase tracking-wider mb-1.5">{label}</p>
      <p className="text-white text-sm font-medium">{String(value ?? "—")}</p>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// ─── BENCHMARK MODAL ──────────────────────────────────────────
// ═══════════════════════════════════════════════════════════════

function PipelineStep({ label, status, detail }) {
  return (
    <div className="flex items-center gap-2.5 py-1.5">
      <div className="w-5 h-5 flex items-center justify-center shrink-0">
        {status === "pending" && <div className="w-2 h-2 rounded-full bg-[#333]" />}
        {status === "running" && (
          <div className="w-4 h-4 border-2 border-[#333] border-t-[#00d4ff] rounded-full"
            style={{ animation: "spin 0.7s linear infinite" }} />
        )}
        {status === "done" && <Check size={14} className="text-[#00ff88]" />}
        {status === "error" && <X size={14} className="text-[#ff4444]" />}
      </div>
      <div className="min-w-0 flex-1">
        <p className={`text-xs leading-tight ${status === "running" ? "text-white" : status === "done" ? "text-[#888]" : "text-[#555]"}`}>
          {label}
        </p>
        {detail && <p className="text-[10px] text-[#555] mt-0.5">{detail}</p>}
      </div>
    </div>
  );
}

function PipelineProgress({ value, color }) {
  return (
    <div className="h-1 rounded-full bg-[#1a1a1a] overflow-hidden mb-4">
      <div className="h-full rounded-full transition-all duration-300 ease-out"
        style={{ width: `${value}%`, background: color }} />
    </div>
  );
}

function BenchmarkModal({ file, preview, onClose, onResults }) {
  const [ocrSteps, setOcrSteps] = useState([
    { label: "Preprocessing image", detail: "OpenCV", status: "pending" },
    { label: "Running OCR engine", detail: "Tesseract", status: "pending" },
    { label: "Cleaning OCR text", detail: null, status: "pending" },
    { label: "Extracting fields", detail: "Regex + Pandas", status: "pending" },
    { label: "Validating document", detail: null, status: "pending" },
    { label: "Formatting output", detail: null, status: "pending" },
  ]);
  const [ocrProgress, setOcrProgress] = useState(0);
  const [ocrDone, setOcrDone] = useState(false);

  const [visionPhase, setVisionPhase] = useState(0);
  const [visionProgress, setVisionProgress] = useState(0);
  const [visionDone, setVisionDone] = useState(false);
  const [scanY, setScanY] = useState(0);

  const [combinedSteps, setCombinedSteps] = useState([
    { label: "Quick OCR pass", detail: "Tesseract", status: "pending" },
    { label: "Text cleanup", detail: null, status: "pending" },
    { label: "Sending to Vision AI", detail: "Llama 4 Scout", status: "pending" },
    { label: "Merging OCR + Vision", detail: "Context fusion", status: "pending" },
    { label: "Cross-validating fields", detail: null, status: "pending" },
    { label: "Best accuracy achieved", detail: null, status: "pending" },
  ]);
  const [combinedProgress, setCombinedProgress] = useState(0);
  const [combinedDone, setCombinedDone] = useState(false);

  const [fetchDone, setFetchDone] = useState(false);
  const [fetchData, setFetchData] = useState(null);
  const [fetchError, setFetchError] = useState(null);
  const [allDone, setAllDone] = useState(false);

  const visionTexts = [
    "Sending image to Llama 4 Scout...",
    "Analyzing document structure...",
    "Identifying fields...",
    "Generating structured output...",
  ];

  // OCR pipeline animation
  useEffect(() => {
    let cancelled = false;
    const timings = [500, 1200, 400, 600, 350, 300];
    (async () => {
      for (let i = 0; i < 6; i++) {
        if (cancelled) return;
        setOcrSteps((prev) => prev.map((s, j) => j === i ? { ...s, status: "running" } : s));
        setOcrProgress(Math.round((i / 6) * 100));
        await sleep(timings[i]);
        if (cancelled) return;
        setOcrSteps((prev) => prev.map((s, j) => j === i ? { ...s, status: "done" } : s));
      }
      setOcrProgress(100);
      setOcrDone(true);
    })();
    return () => { cancelled = true; };
  }, []);

  // Vision pipeline animation
  useEffect(() => {
    let cancelled = false;
    (async () => {
      for (let i = 0; i < 4; i++) {
        if (cancelled) return;
        setVisionPhase(i + 1);
        setVisionProgress(Math.round((i / 4) * 100));
        await sleep(750);
      }
      if (cancelled) return;
      setVisionProgress(100);
      setVisionDone(true);
    })();
    return () => { cancelled = true; };
  }, []);

  // Scan line
  useEffect(() => {
    if (visionDone) return;
    let raf;
    let start = null;
    const dur = 3000;
    const tick = (ts) => {
      if (!start) start = ts;
      const pct = Math.min(((ts - start) % dur) / dur, 1);
      setScanY(pct * 100);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [visionDone]);

  // Combined pipeline animation
  useEffect(() => {
    let cancelled = false;
    const timings = [400, 300, 800, 700, 500, 400];
    (async () => {
      for (let i = 0; i < 6; i++) {
        if (cancelled) return;
        setCombinedSteps((prev) => prev.map((s, j) => j === i ? { ...s, status: "running" } : s));
        setCombinedProgress(Math.round((i / 6) * 100));
        await sleep(timings[i]);
        if (cancelled) return;
        setCombinedSteps((prev) => prev.map((s, j) => j === i ? { ...s, status: "done" } : s));
      }
      setCombinedProgress(100);
      setCombinedDone(true);
    })();
    return () => { cancelled = true; };
  }, []);

  // Real backend call
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const formData = new FormData();
        formData.append("file", file);
        console.log("Enviando archivo:", file.name, file.type, file.size);
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/benchmark`, {
          method: "POST", body: formData,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) { setFetchData(data); setFetchDone(true); }
      } catch (err) {
        console.error("Benchmark fetch error:", err);
        if (!cancelled) { setFetchError(err.message); setFetchDone(true); }
      }
    })();
    return () => { cancelled = true; };
  }, [file]);

  

  // All done check
  useEffect(() => {
    if (ocrDone && visionDone && combinedDone && fetchDone) setAllDone(true);
  }, [ocrDone, visionDone, combinedDone, fetchDone]);

  const globalProgress = Math.round((ocrProgress + visionProgress + combinedProgress) / 3);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.85)", backdropFilter: "blur(12px)" }}>
      <div className="w-full max-w-[940px] bg-[#111] border border-[#2a2a2a] rounded-2xl overflow-hidden shadow-2xl opacity-0"
        style={{ animation: "cardIn 0.4s ease-out forwards" }}>

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a2a2a]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#00d4ff]/10 flex items-center justify-center">
              <Share2 size={16} className="text-[#00d4ff]" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Analyzing your document</h3>
              <p className="text-[10px] text-[#555] mt-0.5">Running 3 pipelines in parallel to compare accuracy</p>
            </div>
          </div>
          <button onClick={onClose}
            className="w-8 h-8 rounded-lg bg-[#1a1a1a] flex items-center justify-center text-[#555] hover:text-white hover:bg-[#222] transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* 3 Pipelines */}
        <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-[#2a2a2a]">

          {/* Pipeline 1: OCR */}
          <div className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <FileText size={14} style={{ color: CYAN }} />
              <span className="text-xs font-semibold text-white">OCR Pipeline</span>
              {ocrDone && <span className="ml-auto text-[9px] px-2 py-0.5 rounded-full bg-[#00ff88]/10 text-[#00ff88] font-medium">Done</span>}
            </div>
            <PipelineProgress value={ocrProgress} color={CYAN} />
            <div className="space-y-0.5">
              {ocrSteps.map((step, i) => <PipelineStep key={i} {...step} />)}
            </div>
          </div>

          {/* Pipeline 2: Vision AI */}
          <div className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <Eye size={14} style={{ color: PURPLE }} />
              <span className="text-xs font-semibold text-white">Vision AI</span>
              {visionDone && <span className="ml-auto text-[9px] px-2 py-0.5 rounded-full bg-[#00ff88]/10 text-[#00ff88] font-medium">Done</span>}
            </div>
            <PipelineProgress value={visionProgress} color={PURPLE} />

            {/* Image with scan */}
            <div className="relative w-full h-32 bg-[#0a0a0a] rounded-lg border border-[#1a1a1a] overflow-hidden mb-3">
              {preview ? (
                <img src={preview} alt="scan" className="w-full h-full object-contain opacity-60" />
              ) : (
                <div className="w-full h-full flex items-center justify-center"><File size={28} className="text-[#333]" /></div>
              )}
              {!visionDone && (
                <>
                  <div className="absolute left-0 right-0 h-[2px] pointer-events-none"
                    style={{ top: `${scanY}%`, background: `linear-gradient(90deg, transparent, ${PURPLE}, ${CYAN}, transparent)`,
                      boxShadow: `0 0 12px 2px ${CYAN}55` }} />
                  <div className="absolute left-0 right-0 h-8 pointer-events-none"
                    style={{ top: `${scanY}%`, background: `linear-gradient(to bottom, ${CYAN}15, transparent)` }} />
                </>
              )}
              {visionDone && (
                <div className="absolute inset-0 flex items-center justify-center bg-[#0a0a0a]/60">
                  <span className="text-xs font-medium text-[#00ff88] flex items-center gap-1.5"><Check size={14} /> Classification complete</span>
                </div>
              )}
            </div>

            <div className="space-y-1">
              {visionTexts.map((txt, i) => (
                <div key={i} className="flex items-center gap-2 py-1">
                  <div className="w-5 h-5 flex items-center justify-center shrink-0">
                    {visionPhase > i + 1 || visionDone ? <Check size={14} className="text-[#00ff88]" />
                      : visionPhase === i + 1 && !visionDone ? <div className="w-4 h-4 border-2 border-[#333] border-t-[#a855f7] rounded-full" style={{ animation: "spin 0.7s linear infinite" }} />
                      : <div className="w-2 h-2 rounded-full bg-[#333]" />}
                  </div>
                  <p className={`text-xs ${visionPhase === i + 1 && !visionDone ? "text-white" : visionPhase > i + 1 || visionDone ? "text-[#888]" : "text-[#555]"}`}>{txt}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Pipeline 3: Combined */}
          <div className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <Brain size={14} style={{ color: GREEN }} />
              <span className="text-xs font-semibold text-white">OCR + Vision</span>
              {combinedDone && <span className="ml-auto text-[9px] px-2 py-0.5 rounded-full bg-[#00ff88]/10 text-[#00ff88] font-medium">Best</span>}
            </div>
            <PipelineProgress value={combinedProgress} color={GREEN} />
            <div className="space-y-0.5">
              {combinedSteps.map((step, i) => <PipelineStep key={i} {...step} />)}
            </div>
            {combinedProgress > 50 && !combinedDone && (
              <div className="mt-3 flex items-center justify-center gap-2 py-2 opacity-0"
                style={{ animation: "cardIn 0.4s ease-out forwards" }}>
                <div className="w-6 h-[2px] rounded-full" style={{ background: CYAN }} />
                <div className="text-[10px] text-[#555]">merging</div>
                <div className="w-6 h-[2px] rounded-full" style={{ background: PURPLE }} />
                <ArrowRight size={10} className="text-[#555]" />
                <div className="w-6 h-[2px] rounded-full" style={{ background: GREEN }} />
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#2a2a2a] flex items-center justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] text-[#555]">{allDone ? "All pipelines complete" : "Running benchmarks..."}</span>
              <span className="text-[10px] font-mono text-[#888]">{globalProgress}%</span>
            </div>
            <div className="h-1 rounded-full bg-[#1a1a1a] overflow-hidden">
              <div className="h-full rounded-full transition-all duration-300"
                style={{ width: `${globalProgress}%`, background: allDone ? GREEN : `linear-gradient(90deg, ${CYAN}, ${PURPLE}, ${GREEN})` }} />
            </div>
          </div>
          <button
            onClick={() => { if (fetchData) onResults(fetchData); else onClose(); }}
            disabled={!allDone}
            className={`shrink-0 px-5 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
              allDone ? "btn-primary" : "bg-[#1a1a1a] text-[#555] cursor-not-allowed"
            }`}>
            {!allDone ? (
              <><div className="w-3.5 h-3.5 border-2 border-[#555] border-t-[#00d4ff] rounded-full" style={{ animation: "spin 0.7s linear infinite" }} /> Processing...</>
            ) : fetchError ? (
              <><AlertCircle size={14} /> Close (API error)</>
            ) : (
              <><Eye size={14} /> View Results</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// ─── MAIN APP ─────────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════════
export default function DocuScanAI() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [benchmarkData, setBenchmarkData] = useState(null);
  const [activeTab, setActiveTab] = useState("ocr");
  const [copied, setCopied] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const appRef = useRef(null);
  const fileInput = useRef(null);

  const scrollToApp = () => appRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });

  const handleFile = useCallback((f) => {
    if (!f) return;
    setFile(f); setResult(null); setBenchmarkData(null); setStatus("idle"); setActiveTab("ocr");
    if (f.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target.result);
      reader.readAsDataURL(f);
    } else { setPreview(null); }
  }, []);

  const processDocument = () => { if (file) setShowModal(true); };

  const handleBenchmarkResults = (data) => {
    setShowModal(false);
    setBenchmarkData(data);
    setResult(data.combined || data.vision_only || data.ocr_only || {});
    setStatus("done");
    setActiveTab("ocr");
  };

  const copyJSON = () => {
    navigator.clipboard.writeText(JSON.stringify(benchmarkData || result, null, 2));
    setCopied(true); setTimeout(() => setCopied(false), 2000);
  };

  const onDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const onDragLeave = () => setDragOver(false);
  const onDrop = (e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files?.[0]; if (f) handleFile(f); };

  const hasBenchmark = !!benchmarkData;
  const tabs = hasBenchmark
    ? [{ id: "ocr", label: "OCR Only", color: CYAN }, { id: "vision", label: "Vision AI", color: PURPLE }, { id: "combined", label: "OCR + Vision", color: GREEN }]
    : [{ id: "fields", label: "Extracted Fields" }, { id: "json", label: "JSON" }, { id: "summary", label: "Summary" }];

  const getActivePipeline = () => {
    if (!benchmarkData) return null;
    if (activeTab === "ocr") return benchmarkData.ocr_only;
    if (activeTab === "vision") return benchmarkData.vision_only;
    if (activeTab === "combined") return benchmarkData.combined;
    return null;
  };
  const activePipeline = getActivePipeline();
  const activeColor = tabs.find((t) => t.id === activeTab)?.color || CYAN;

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white" style={{ fontFamily: "'Instrument Sans', 'SF Pro Display', system-ui, sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        @keyframes particleFade{0%,100%{opacity:0;transform:translateY(0)}50%{opacity:1;transform:translateY(-12px)}}
        @keyframes cardIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
        @keyframes heroIn{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:translateY(0)}}
        @keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
        @keyframes dragPulse{0%,100%{border-color:rgba(0,212,255,0.3)}50%{border-color:rgba(0,212,255,0.8)}}
        @keyframes spin{to{transform:rotate(360deg)}}
        .hero-anim{animation:heroIn .8s ease-out both}
        .hero-anim-d1{animation:heroIn .8s .15s ease-out both}
        .hero-anim-d2{animation:heroIn .8s .3s ease-out both}
        .hero-anim-d3{animation:heroIn .8s .45s ease-out both}
        .btn-primary{background:#00d4ff;color:#000;font-weight:600;transition:all .2s}
        .btn-primary:hover{background:#00e5ff;box-shadow:0 0 24px rgba(0,212,255,.35)}
        .btn-outline{border:1px solid #333;color:#ccc;transition:all .2s}
        .btn-outline:hover{border-color:#00d4ff;color:#00d4ff}
        .skeleton{background:linear-gradient(90deg,#1a1a1a 25%,#252525 50%,#1a1a1a 75%);background-size:200% 100%;animation:shimmer 1.5s infinite;border-radius:8px}
        .drag-pulse{animation:dragPulse 1s ease-in-out infinite}
        .code-block{font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.6;background:#111;color:#d4d4d4;overflow-x:auto;tab-size:2}
        ::-webkit-scrollbar{width:6px;height:6px}::-webkit-scrollbar-track{background:#111}::-webkit-scrollbar-thumb{background:#333;border-radius:3px}
      `}</style>

      {showModal && <BenchmarkModal file={file} preview={preview} onClose={() => setShowModal(false)} onResults={handleBenchmarkResults} />}

      {/* NAVBAR */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/[0.06]" style={{ background: "rgba(10,10,10,0.85)", backdropFilter: "blur(16px)" }}>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#00d4ff]/10 flex items-center justify-center"><FileText size={18} className="text-[#00d4ff]" /></div>
            <span className="font-bold text-lg tracking-tight">DocuScan AI</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="#how" className="text-sm text-[#888] hover:text-white transition-colors">How it works</a>
            <a href="#docs" className="text-sm text-[#888] hover:text-white transition-colors">Docs</a>
            <button onClick={scrollToApp} className="btn-primary text-sm px-4 py-2 rounded-lg flex items-center gap-1.5">Try it free <ArrowRight size={14} /></button>
          </div>
          <button className="md:hidden p-2 text-[#888]" onClick={() => setMobileMenu(!mobileMenu)}>{mobileMenu ? <X size={22} /> : <Menu size={22} />}</button>
        </div>
        {mobileMenu && (
          <div className="md:hidden border-t border-white/[0.06] px-4 py-4 flex flex-col gap-3" style={{ background: "rgba(10,10,10,0.95)" }}>
            <a href="#how" className="text-sm text-[#888] py-2">How it works</a>
            <button onClick={() => { scrollToApp(); setMobileMenu(false); }} className="btn-primary text-sm px-4 py-2.5 rounded-lg mt-1">Try it free</button>
          </div>
        )}
      </nav>

      {/* HERO */}
      <section className="relative pt-32 pb-20 sm:pt-40 sm:pb-28 overflow-hidden">
        <Particles />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[500px] pointer-events-none" style={{ background: "radial-gradient(ellipse at center, rgba(0,212,255,0.08) 0%, transparent 70%)" }} />
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <div className="hero-anim inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[#00d4ff]/20 bg-[#00d4ff]/[0.06] mb-8">
            <Zap size={14} className="text-[#00d4ff]" /><span className="text-xs font-medium text-[#00d4ff]">Powered by Claude AI</span>
          </div>
          <h1 className="hero-anim-d1 text-4xl sm:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.08] mb-6">Any document.<br /><span className="text-[#00d4ff]">Structured</span> in seconds.</h1>
          <p className="hero-anim-d2 text-base sm:text-lg text-[#888] max-w-xl mx-auto mb-10 leading-relaxed">Upload any invoice, receipt, contract or ID.<br className="hidden sm:block" />Our AI reads, classifies and extracts every field automatically.</p>
          <div className="hero-anim-d3 flex flex-col sm:flex-row items-center justify-center gap-3 mb-6">
            <button onClick={scrollToApp} className="btn-primary px-7 py-3 rounded-xl text-sm flex items-center gap-2 w-full sm:w-auto justify-center"><Upload size={16} /> Upload Document</button>
            <a href="#how" className="btn-outline px-7 py-3 rounded-xl text-sm flex items-center gap-2 w-full sm:w-auto justify-center"><Eye size={16} /> See how it works</a>
          </div>
          <p className="text-xs text-[#555]">Supports PDF, JPG, PNG · No signup required</p>
        </div>
      </section>

      {/* THE APP */}
      <section ref={appRef} className="relative py-16 sm:py-24" id="app">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight mb-3">Try it now</h2>
            <p className="text-sm text-[#888]">Upload a document and watch the AI extract structured data in real time.</p>
          </div>
          <div className="grid lg:grid-cols-2 gap-6">

            {/* LEFT: Upload */}
            <div className="bg-[#111] border border-[#2a2a2a] rounded-2xl p-6 flex flex-col">
              <div className="flex items-center gap-2 mb-5"><Upload size={16} className="text-[#00d4ff]" /><h3 className="font-semibold text-sm">Upload Document</h3></div>
              {!file ? (
                <div onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop} onClick={() => fileInput.current?.click()}
                  className={`flex-1 min-h-[260px] border-2 border-dashed rounded-xl flex flex-col items-center justify-center cursor-pointer transition-all ${dragOver ? "border-[#00d4ff] bg-[#00d4ff]/[0.04] drag-pulse" : "border-[#2a2a2a] hover:border-[#00d4ff]/40 hover:bg-white/[0.01]"}`}>
                  <div className="w-14 h-14 rounded-2xl bg-[#1a1a1a] flex items-center justify-center mb-4"><Upload size={24} className="text-[#555]" /></div>
                  <p className="text-sm text-[#ccc] font-medium mb-1">Drop your document here</p>
                  <p className="text-xs text-[#555]">or click to browse</p>
                  <div className="flex items-center gap-2 mt-4">
                    {["PDF", "JPG", "PNG", "TIFF"].map((fmt) => <span key={fmt} className="text-[10px] px-2 py-0.5 rounded bg-[#1a1a1a] text-[#666] font-mono">{fmt}</span>)}
                  </div>
                  <input ref={fileInput} type="file" accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif" className="hidden" onChange={(e) => handleFile(e.target.files?.[0])} />
                </div>
              ) : (
                <div className="flex-1 flex flex-col">
                  <div className="flex-1 bg-[#0a0a0a] rounded-xl border border-[#1a1a1a] overflow-hidden flex items-center justify-center mb-4 min-h-[200px]">
                    {preview ? <img src={preview} alt="preview" className="max-h-[240px] object-contain" /> : <div className="flex flex-col items-center text-[#555]"><File size={40} className="mb-2" /><span className="text-xs font-mono">{file.name}</span></div>}
                  </div>
                  <div className="flex items-center justify-between bg-[#0a0a0a] rounded-lg px-4 py-3 mb-4 border border-[#1a1a1a]">
                    <div className="flex items-center gap-3 min-w-0">
                      <ImageIcon size={16} className="text-[#555] shrink-0" />
                      <div className="min-w-0"><p className="text-xs text-white truncate">{file.name}</p><p className="text-[10px] text-[#555]">{(file.size / 1024).toFixed(1)} KB</p></div>
                    </div>
                    <button onClick={() => { setFile(null); setPreview(null); setResult(null); setBenchmarkData(null); setStatus("idle"); }} className="text-[#555] hover:text-[#ff4444] transition-colors p-1"><X size={14} /></button>
                  </div>
                  <button onClick={processDocument}
                    className={`w-full py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all ${status === "done" ? "bg-[#00ff88]/10 text-[#00ff88] border border-[#00ff88]/20" : "btn-primary"}`}>
                    {status === "done" ? <><Check size={16} /> Processed — click to re-run</> : <><Share2 size={16} /> Process Document</>}
                  </button>
                </div>
              )}
            </div>

            {/* RIGHT: Results */}
            <div className="bg-[#111] border border-[#2a2a2a] rounded-2xl p-6 flex flex-col">
              <div className="flex items-center gap-2 mb-5">
                <Brain size={16} className="text-[#00d4ff]" /><h3 className="font-semibold text-sm">Extracted Data</h3>
                {hasBenchmark && <span className="ml-auto text-[9px] px-2 py-0.5 rounded-full bg-[#00d4ff]/10 text-[#00d4ff] font-medium">Benchmark Mode</span>}
              </div>

              {!result ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center min-h-[300px]">
                  <div className="flex flex-wrap justify-center gap-2 mb-6 max-w-sm">
                    {["INVOICE", "RECEIPT", "CONTRACT", "ID CARD", "BANK STATEMENT"].map((t) => (
                      <span key={t} className="text-[10px] font-mono px-2.5 py-1 rounded-md border"
                        style={{ borderColor: (DOC_TYPE_COLORS[t] || "#555") + "33", color: DOC_TYPE_COLORS[t] || "#555", background: (DOC_TYPE_COLORS[t] || "#555") + "08" }}>{t}</span>
                    ))}
                  </div>
                  <p className="text-sm text-[#555]">Your extracted data will appear here</p>
                </div>
              ) : (
                <div className="flex-1 flex flex-col min-h-[300px]">
                  {/* Tabs */}
                  <div className="flex gap-1 p-1 bg-[#0a0a0a] rounded-lg mb-4">
                    {tabs.map((tab) => (
                      <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                        className={`flex-1 text-xs py-2 rounded-md transition-all font-medium ${activeTab === tab.id ? "bg-[#1a1a1a] text-white" : "text-[#666] hover:text-[#999]"}`}>
                        <span className="flex items-center justify-center gap-1.5">
                          {tab.color && <span className="w-1.5 h-1.5 rounded-full" style={{ background: tab.color }} />}
                          {tab.label}
                        </span>
                      </button>
                    ))}
                  </div>

                  <div className="flex-1 overflow-y-auto pr-1" style={{ maxHeight: 420 }}>
                    {hasBenchmark && activePipeline ? (
                      <BenchmarkTabContent data={activePipeline} color={activeColor} tabId={activeTab} />
                    ) : !hasBenchmark && result ? (
                      <LegacyTabContent result={result} activeTab={activeTab} copied={copied} copyJSON={copyJSON} />
                    ) : null}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="py-16 sm:py-24">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight mb-3">How it works</h2>
            <p className="text-sm text-[#888]">Three steps. Zero configuration.</p>
          </div>
          <div className="grid sm:grid-cols-3 gap-6">
            {[
              { icon: Upload, step: "01", title: "Upload", desc: "Drag & drop any document — invoice, receipt, contract, ID, or anything else.", color: CYAN },
              { icon: Eye, step: "02", title: "Process", desc: "OCR extracts raw text from every corner of your document with high accuracy.", color: PURPLE },
              { icon: Brain, step: "03", title: "Understand", desc: "AI classifies the document type and structures every field into clean JSON.", color: GREEN },
            ].map((s, i) => (
              <div key={i} className="bg-[#111] border border-[#2a2a2a] rounded-2xl p-6 hover:border-[#333] transition-colors group">
                <div className="flex items-center justify-between mb-5">
                  <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: s.color + "10" }}><s.icon size={20} style={{ color: s.color }} /></div>
                  <span className="text-3xl font-bold text-[#1a1a1a] group-hover:text-[#222] transition-colors">{s.step}</span>
                </div>
                <h3 className="font-semibold text-lg mb-2">{s.title}</h3>
                <p className="text-sm text-[#888] leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* DOCUMENT TYPES */}
      <section className="py-16 sm:py-24 border-t border-white/[0.04]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight mb-3">Works with any document</h2>
            <p className="text-sm text-[#888]">Built to handle the messiest, most complex documents in the world.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {DOC_TYPES.map((doc, i) => (
              <div key={i} className="bg-[#111] border border-[#2a2a2a] rounded-xl p-4 flex items-start gap-3.5 hover:border-[#333] transition-colors group cursor-default">
                <div className="w-9 h-9 rounded-lg bg-[#1a1a1a] flex items-center justify-center shrink-0 group-hover:bg-[#222] transition-colors">
                  <doc.icon size={16} className="text-[#666] group-hover:text-[#00d4ff] transition-colors" />
                </div>
                <div><h4 className="text-sm font-medium mb-0.5">{doc.name}</h4><p className="text-xs text-[#666] leading-relaxed">{doc.desc}</p></div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-white/[0.06] py-12">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-md bg-[#00d4ff]/10 flex items-center justify-center"><FileText size={14} className="text-[#00d4ff]" /></div>
              <span className="font-semibold text-sm">DocuScan AI</span>
              <span className="text-xs text-[#444]">·</span>
              <span className="text-xs text-[#444]">Scan anything, structure everything</span>
            </div>
            <div className="flex items-center gap-6">
              <a href="#" className="text-xs text-[#666] hover:text-white transition-colors flex items-center gap-1.5"><BookOpen size={13} /> Docs</a>
              <a href="#" className="text-xs text-[#666] hover:text-white transition-colors flex items-center gap-1.5"><Code2 size={13} /> API</a>
            </div>
          </div>
          <div className="mt-8 pt-6 border-t border-white/[0.04] text-center">
            <p className="text-[11px] text-[#444]">Built with Next.js and FastAPI · {new Date().getFullYear()}</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// ─── BENCHMARK TAB CONTENT ────────────────────────────────────
// ═══════════════════════════════════════════════════════════════
function BenchmarkTabContent({ data, color, tabId }) {
  if (!data) return <p className="text-sm text-[#555]">No data available for this pipeline.</p>;
  const fields = data.fields || {};
  const docType = data.document_type || "UNKNOWN";
  const confidence = data.confidence || 0;
  const typeColor = DOC_TYPE_COLORS[docType] || "#6b7280";
  const pipelineLabels = { ocr: "OCR Only", vision: "Vision AI", combined: "OCR + Vision (Best)" };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-[10px] px-2 py-0.5 rounded-full font-medium" style={{ background: color + "15", color, border: `1px solid ${color}30` }}>
          {pipelineLabels[tabId] || tabId}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-xs font-bold px-3 py-1 rounded-md uppercase tracking-wider"
          style={{ background: typeColor + "18", color: typeColor, border: `1px solid ${typeColor}33` }}>{docType}</span>
      </div>
      <ConfidenceBar label="Confidence" value={confidence} color={color} />
      <div className="grid grid-cols-2 gap-3">
        {Object.entries(fields).map(([key, val], i) => {
          if (typeof val === "object" && val !== null) return null;
          return <FieldCard key={key} label={key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())} value={String(val ?? "—")} delay={i * 50} />;
        })}
      </div>
      {Object.entries(fields).map(([key, val]) => {
        if (typeof val !== "object" || val === null || Array.isArray(val)) return null;
        return (
          <div key={key}>
            <p className="text-xs text-[#555] uppercase tracking-wider mb-2 mt-2">{key.replace(/_/g, " ")}</p>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(val).map(([k2, v2], j) => <FieldCard key={k2} label={k2.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())} value={String(v2 ?? "—")} delay={j * 50} />)}
            </div>
          </div>
        );
      })}
      {fields.line_items && Array.isArray(fields.line_items) && fields.line_items.length > 0 && (
        <div className="bg-[#111] border border-[#2a2a2a] rounded-xl overflow-hidden opacity-0" style={{ animation: "cardIn 0.5s 200ms ease-out forwards" }}>
          <div className="px-4 py-2.5 border-b border-[#2a2a2a]"><p className="text-xs text-[#666] uppercase tracking-wider">Line Items</p></div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-[#555] border-b border-[#1a1a1a]"><th className="text-left px-4 py-2 font-medium">Description</th><th className="text-right px-4 py-2 font-medium">Qty</th><th className="text-right px-4 py-2 font-medium">Price</th><th className="text-right px-4 py-2 font-medium">Total</th></tr></thead>
              <tbody>
                {fields.line_items.map((item, i) => (
                  <tr key={i} className="border-b border-[#1a1a1a]/50 hover:bg-white/[0.01]">
                    <td className="px-4 py-2.5 text-white">{item.description || "—"}</td>
                    <td className="px-4 py-2.5 text-[#888] text-right">{item.quantity ?? "—"}</td>
                    <td className="px-4 py-2.5 text-[#888] text-right font-mono">{item.unit_price != null ? `$${Number(item.unit_price).toFixed(2)}` : "—"}</td>
                    <td className="px-4 py-2.5 text-white text-right font-mono">{item.total != null ? `$${Number(item.total).toFixed(2)}` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {data.summary && (
        <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-5 opacity-0" style={{ animation: "cardIn 0.5s 300ms ease-out forwards" }}>
          <div className="flex items-center gap-2 mb-3"><Sparkles size={14} style={{ color }} /><span className="text-xs font-medium" style={{ color }}>AI Summary</span></div>
          <p className="text-sm text-[#ccc] leading-relaxed">{data.summary}</p>
        </div>
      )}
      <details className="group">
        <summary className="text-xs text-[#555] cursor-pointer hover:text-[#888] transition-colors flex items-center gap-1.5 py-2">
          <ChevronDown size={12} className="group-open:rotate-180 transition-transform" />View raw JSON
        </summary>
        <pre className="code-block p-4 rounded-xl border border-[#2a2a2a] whitespace-pre-wrap mt-2 text-[11px]">{formatJSON(data)}</pre>
      </details>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// ─── LEGACY TAB CONTENT ───────────────────────────────────────
// ═══════════════════════════════════════════════════════════════
function LegacyTabContent({ result, activeTab, copied, copyJSON }) {
  const typeColor = DOC_TYPE_COLORS[result.document_type] || "#6b7280";
  if (activeTab === "fields") {
    return (
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3 mb-2">
          <span className="text-xs font-bold px-3 py-1 rounded-md uppercase tracking-wider" style={{ background: typeColor + "18", color: typeColor, border: `1px solid ${typeColor}33` }}>{result.document_type}</span>
          {result.processing_time_ms && <div className="flex items-center gap-1.5 text-xs text-[#888]"><Clock size={12} />{result.processing_time_ms}ms</div>}
        </div>
        <ConfidenceBar label="Classification" value={result.confidence || 0} color={typeColor} />
        {result.ocr_confidence != null && <ConfidenceBar label="OCR Quality" value={result.ocr_confidence} color={GREEN} />}
        <div className="grid grid-cols-2 gap-3 mt-2">
          <FieldCard label="Document Type" value={result.document_type} delay={0} />
          <FieldCard label="Vendor" value={result.vendor?.name} delay={60} />
          <FieldCard label="Date" value={result.date} delay={120} />
          <FieldCard label="Total" value={result.total != null ? `$${result.total} ${result.currency_code || ""}` : "—"} delay={180} />
          <FieldCard label="Doc Number" value={result.document_number ? `#${result.document_number}` : "—"} delay={240} />
          <FieldCard label="Payment" value={result.payment_method} delay={300} />
        </div>
        {result.vendor?.address && <FieldCard label="Vendor Address" value={result.vendor.address} delay={360} />}
        {result.line_items?.length > 0 && (
          <div className="bg-[#111] border border-[#2a2a2a] rounded-xl overflow-hidden opacity-0" style={{ animation: "cardIn 0.5s 420ms ease-out forwards" }}>
            <div className="px-4 py-2.5 border-b border-[#2a2a2a]"><p className="text-xs text-[#666] uppercase tracking-wider">Line Items</p></div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead><tr className="text-[#555] border-b border-[#1a1a1a]"><th className="text-left px-4 py-2 font-medium">Description</th><th className="text-right px-4 py-2 font-medium">Qty</th><th className="text-right px-4 py-2 font-medium">Price</th><th className="text-right px-4 py-2 font-medium">Total</th></tr></thead>
                <tbody>{result.line_items.map((item, i) => (
                  <tr key={i} className="border-b border-[#1a1a1a]/50 hover:bg-white/[0.01]">
                    <td className="px-4 py-2.5 text-white">{item.description}</td><td className="px-4 py-2.5 text-[#888] text-right">{item.quantity}</td>
                    <td className="px-4 py-2.5 text-[#888] text-right font-mono">{item.unit_price != null ? `$${item.unit_price.toFixed(2)}` : "—"}</td>
                    <td className="px-4 py-2.5 text-white text-right font-mono">{item.total != null ? `$${item.total.toFixed(2)}` : "—"}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  }
  if (activeTab === "json") {
    return (
      <div className="relative">
        <div className="absolute top-2 right-2 flex gap-1.5 z-10">
          <button onClick={copyJSON} className="flex items-center gap-1 text-[10px] px-2.5 py-1.5 rounded-md bg-[#1a1a1a] text-[#888] hover:text-white border border-[#2a2a2a] transition-colors">
            {copied ? <Check size={12} className="text-[#00ff88]" /> : <Copy size={12} />}{copied ? "Copied" : "Copy"}
          </button>
          <button className="flex items-center gap-1 text-[10px] px-2.5 py-1.5 rounded-md bg-[#1a1a1a] text-[#888] hover:text-white border border-[#2a2a2a] transition-colors"><Download size={12} /> JSON</button>
        </div>
        <pre className="code-block p-4 rounded-xl border border-[#2a2a2a] whitespace-pre-wrap">{formatJSON(result)}</pre>
      </div>
    );
  }
  if (activeTab === "summary") {
    return (
      <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-5 opacity-0" style={{ animation: "cardIn 0.5s ease-out forwards" }}>
        <div className="flex items-center gap-2 mb-3"><Sparkles size={14} className="text-[#00d4ff]" /><span className="text-xs font-medium text-[#00d4ff]">AI Summary</span></div>
        <p className="text-sm text-[#ccc] leading-relaxed">{result.summary || "No summary available."}</p>
      </div>
    );
  }
  return null;
}