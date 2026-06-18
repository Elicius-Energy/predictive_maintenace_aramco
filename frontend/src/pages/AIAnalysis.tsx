import { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { FC } from 'react';
import { useMachine } from '../contexts/MachineContext';
import { useChat } from '../contexts/ChatContext';
import { useSensorData } from '../hooks/useSensorData';
import FormulaPanel from '../components/common/FormulaPanel';
import { FORMULAS } from '../data/formulas';
import { BACKEND_URL } from '../utils/constants';
import { useReactToPrint } from 'react-to-print';
import { PdfReportTemplate } from '../components/report/PdfReportTemplate';
import { useHistory } from '../contexts/HistoryContext';
import {
  BrainCircuit,
  Settings2,
  TrendingUp,
  MessageSquare,
  Bot,
  User,
  Send,
  BarChart3,
  DollarSign,
  Download
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
  BarChart,
  Bar
} from 'recharts';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type Mode = 'current' | 'fleet';

const AIAnalysis: FC = () => {
  const { activeMachine, selectedWindow } = useMachine();
  const { messages, setMessages } = useChat();
  const { latestFeatures, latestHealth } = useSensorData();
  const { mechanicalHistory, electricalHistory } = useHistory();
  const [mode, setMode] = useState<Mode>('current');
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const pdfRef = useRef<HTMLDivElement>(null);

  // Machine-specific ROI data profiles (Relative Percentages)
  const MACHINE_ROI_PROFILES: Record<string, any[]> = {
    'sim-pump-001': [
      { month: 'M1', efficiencyGain: 0, riskReduction: 0 },
      { month: 'M3', efficiencyGain: 2, riskReduction: 10 },
      { month: 'M6', efficiencyGain: 3.2, riskReduction: 25 },
      { month: 'M9', efficiencyGain: 4.0, riskReduction: 40 },
      { month: 'M12', efficiencyGain: 4.5, riskReduction: 55 }
    ],
    'sim-pump-002': [
      { month: 'M1', efficiencyGain: 0, riskReduction: 0 },
      { month: 'M3', efficiencyGain: 5, riskReduction: 15 },
      { month: 'M6', efficiencyGain: 8, riskReduction: 38 },
      { month: 'M9', efficiencyGain: 12, riskReduction: 60 },
      { month: 'M12', efficiencyGain: 15, riskReduction: 80 }
    ],
    'sim-motor-003': [
      { month: 'M1', efficiencyGain: 0, riskReduction: 0 },
      { month: 'M3', efficiencyGain: 8, riskReduction: 20 },
      { month: 'M6', efficiencyGain: 18, riskReduction: 55 },
      { month: 'M9', efficiencyGain: 25, riskReduction: 75 },
      { month: 'M12', efficiencyGain: 35, riskReduction: 92 }
    ],
    'Machine_10': [
      { month: 'M1', efficiencyGain: 0, riskReduction: 0 },
      { month: 'M3', efficiencyGain: 3, riskReduction: 8 },
      { month: 'M6', efficiencyGain: 6, riskReduction: 18 },
      { month: 'M9', efficiencyGain: 9, riskReduction: 32 },
      { month: 'M12', efficiencyGain: 14, riskReduction: 50 }
    ]
  };

  const MACHINE_RISK_BREAKDOWN: Record<string, any[]> = {
    'sim-pump-001': [{ component: 'Bearings', risk: 15 }, { component: 'Impeller', risk: 5 }, { component: 'Seals', risk: 20 }],
    'sim-pump-002': [{ component: 'Bearings', risk: 35 }, { component: 'Impeller', risk: 60 }, { component: 'Seals', risk: 25 }],
    'sim-motor-003': [{ component: 'Stator', risk: 85 }, { component: 'Rotor', risk: 40 }, { component: 'Bearings', risk: 75 }],
    'Machine_10': [{ component: 'Bearings', risk: 10 }, { component: 'Impeller', risk: 15 }, { component: 'Seals', risk: 5 }],
  };

  const activeId = activeMachine?.machine_id || 'sim-pump-001';
  const roiData = MACHINE_ROI_PROFILES[activeId] || MACHINE_ROI_PROFILES['sim-pump-001'];
  const riskData = MACHINE_RISK_BREAKDOWN[activeId] || MACHINE_RISK_BREAKDOWN['sim-pump-001'];

  // Machine-specific justifications
  const machineJustifications: Record<string, string> = {
    'sim-pump-001': "Baseline optimization project. ROI is driven by a 3.2% efficiency gain via precision shaft alignment and automated lubrication scheduling.",
    'sim-pump-002': "Proactive impeller restoration project. Savings are predominantly from preventing $15k in hydraulic cavitation damage and reducing energy waste by 8%.",
    'sim-motor-003': "Critical Compressor Protection. High ROI is achieved by preventing a projected catastrophic winding failure that would result in $750k in production downtime for Yanbu Line 4."
  };

  const currentJustification = mode === 'current' 
    ? (machineJustifications[activeId] || "Fleet-wide predictive maintenance strategy.")
    : "Implementing a fleet-wide predictive alignment strategy will yield a projected annual saving of $2.4M across all units.";

  const latestAssistantSummary = [...messages]
    .reverse()
    .find((message) => message.role === 'assistant')?.content
    ?.replace(/[#>*_`-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const energyWaste =
    mode === 'current'
      ? (activeId === 'sim-motor-003' ? '12.8' : (activeId === 'sim-pump-002' ? '6.4' : '1.2'))
      : '20.4';

  const downtimeDays =
    mode === 'current'
      ? (activeId === 'sim-motor-003' ? '14' : (activeId === 'sim-pump-002' ? '85' : '320'))
      : '410';

  const healthMetric = latestFeatures?.health_score ?? latestHealth?.health_score ?? 0;
  const anomalyMetric = (latestFeatures?.anomaly_score ?? 0) * 100;
  const reportSummary = latestAssistantSummary || `${currentJustification} Current machine health is ${healthMetric.toFixed(1)}% with anomaly exposure at ${anomalyMetric.toFixed(1)}%.`;

  const handleDownloadPdf = useReactToPrint({
    contentRef: pdfRef,
    documentTitle: `ai-analysis-${activeId}-${selectedWindow}m`,
  });

  // Use the env variable if injected by Vite, otherwise a fallback name for display
  const modelName = import.meta.env.VITE_ANTHROPIC_MODEL || 'Claude 3.5 Haiku';

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput.trim();
    const currentHistory = [...messages];

    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setChatInput('');
    setIsTyping(true);

    try {
      const response = await fetch(`${BACKEND_URL}/api/rag/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg,
          machine_id: activeMachine?.machine_id || 'sim-pump-001',
          history: currentHistory
        })
      });

      if (!response.ok) throw new Error('Failed to reach AI Backend');

      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
    } catch (err) {
      console.error('Chat Error:', err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'I managed to encounter an error connecting to the AI server. Please ensure the backend is running with a valid Anthropic API key.'
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex justify-between items-end flex-shrink-0">
        <div className="flex items-center gap-3">
          <BrainCircuit className="text-primary" size={28} />
          <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">AI RAG Analysis</h2>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => window.open(`${BACKEND_URL}/api/data/download_csv?machine_id=${activeId}&minutes=${selectedWindow}`)}
            className="flex items-center gap-2 px-3 py-1.5 bg-surface-muted hover:bg-surface border border-border rounded-lg text-xs font-bold text-text-primary transition-colors cursor-pointer"
          >
            <Download size={14} />
            CSV Export
          </button>
          <button
            onClick={() => handleDownloadPdf()}
            className="flex items-center gap-2 px-3 py-1.5 bg-primary text-white hover:bg-primary-dark border border-primary rounded-lg text-xs font-bold transition-colors cursor-pointer"
          >
            <Download size={14} />
            PDF Report
          </button>
          <span className="px-3 py-1.5 bg-surface-muted rounded-lg text-xs font-semibold text-text-secondary border border-border">LLM ENGINE: {modelName.toUpperCase()}</span>
        </div>
      </div>

      {/* Mode Toggles */}
      <div className="flex gap-4 flex-shrink-0">
        <button
          onClick={() => setMode('current')}
          className={cn(
            "px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all",
            mode === 'current' ? "bg-primary text-white shadow-md" : "bg-surface text-text-secondary hover:bg-surface-muted border border-border"
          )}
        >
          <Settings2 size={18} />
          Current Asset Analysis
        </button>
        <button
          onClick={() => setMode('fleet')}
          className={cn(
            "px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all",
            mode === 'fleet' ? "bg-primary text-white shadow-md" : "bg-surface text-text-secondary hover:bg-surface-muted border border-border"
          )}
        >
          <TrendingUp size={18} />
          Fleet Cross-Unit Analysis
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0 flex-1 max-h-[calc(100vh-200px)]">
        {/* Left Column: Business Insights / ROI */}
        <div className="space-y-6 overflow-y-auto pr-2 pb-4">
          <div className="industrial-card p-6 bg-gradient-to-br from-surface to-surface-muted">
            <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider mb-4 flex items-center gap-2">
              <BarChart3 className="text-primary" size={18} />
              {mode === 'current' ? `Running Conditions: ${activeMachine?.name || 'Selected Asset'}` : 'Global Fleet Conditions'}
            </h3>

            <div className="space-y-4">
              <p className="text-sm text-text-secondary leading-relaxed">
                {mode === 'current'
                  ? `The current asset is experiencing optimal load factors, but historical RAG data suggests that running continuously at 90%+ load increases thermal degradation by 12%. Immediate risk is low, but long-term wear is accumulating.`
                  : `Across the 3 actively monitored units, average efficiency is at 88%. Unit P-202 is currently dragging down the fleet average due to a higher apparent power (kVA) draw compared to active power (kW).`
                }
              </p>

              <div className="grid grid-cols-2 gap-4 pt-4">
                <div className="p-4 bg-surface rounded-xl border border-border">
                  <p className="text-xs text-text-muted uppercase font-bold tracking-tight">Energy Waste (Est)</p>
                  <p className="text-2xl font-extrabold text-accent-red scada-number mt-1">
                    {energyWaste} <span className="text-sm text-text-muted">kWh/day</span>
                  </p>
                </div>
                <div className="p-4 bg-surface rounded-xl border border-border">
                  <p className="text-xs text-text-muted uppercase font-bold tracking-tight">Predicted Downtime</p>
                  <p className="text-2xl font-extrabold text-accent-amber scada-number mt-1">
                    {downtimeDays} <span className="text-sm text-text-muted">Days away</span>
                  </p>
                </div>
              </div>
            </div>
            <FormulaPanel items={FORMULAS.aiAnalytics} />
          </div>

          <div className="industrial-card p-6 border-l-4 border-l-primary">
            <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider mb-4 flex items-center gap-2">
              <DollarSign className="text-accent-green" size={18} />
              Return On Investment (ROI) Projection
            </h3>
            <p className="text-sm text-text-secondary leading-relaxed mb-4">
              {currentJustification}
            </p>

            <div className="h-56 w-full mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={roiData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorEff" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border)" opacity={0.5} />
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--color-text-muted)' }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--color-text-muted)' }} tickFormatter={(val) => `${val}%`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)', borderRadius: '8px' }}
                    itemStyle={{ color: 'var(--color-text-primary)' }}
                    formatter={(value: any) => [`${Number(value)}%`, undefined]}
                  />
                  <Area type="monotone" dataKey="efficiencyGain" name="Efficiency Gain (%)" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorEff)" />
                  <Area type="monotone" dataKey="riskReduction" name="Downtime Risk Reduction (%)" stroke="#8b5cf6" strokeWidth={2} fillOpacity={1} fill="url(#colorRisk)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <FormulaPanel items={FORMULAS.aiAnalytics} />
          </div>

          <div className="industrial-card p-6 border-l-4 border-l-amber-500">
            <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider mb-4 flex items-center gap-2">
              <BarChart3 className="text-amber-500" size={18} />
              Component Vulnerability Matrix
            </h3>
            <div className="h-48 w-full mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={riskData} layout="vertical" margin={{ top: 0, right: 20, left: 20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={true} stroke="var(--color-border)" opacity={0.3} />
                  <XAxis type="number" hide domain={[0, 100]} />
                  <YAxis type="category" dataKey="component" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--color-text-primary)', fontWeight: 'bold' }} width={80} />
                  <Tooltip cursor={{ fill: 'var(--color-surface-muted)' }} contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)', borderRadius: '8px' }} formatter={(value: any) => [`${value}%`, 'Current Risk Profile']} />
                  <Bar dataKey="risk" fill="#f59e0b" radius={[0, 4, 4, 0]} barSize={20} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <FormulaPanel items={[...FORMULAS.bearingHealth, ...FORMULAS.imbalance, ...FORMULAS.aiAnalytics]} />
          </div>
        </div>

        {/* Right Column: AI Chat Interface */}
        <div className="industrial-card flex flex-col h-full overflow-hidden border border-border">
          <div className="p-4 border-b border-border bg-surface-muted flex items-center gap-2">
            <MessageSquare size={18} className="text-text-secondary" />
            <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">Interactive RAG Chat</h3>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-surface">
            {messages.map((msg, i) => (
              <div key={i} className={cn("flex gap-3", msg.role === 'user' ? "flex-row-reverse" : "flex-row")}>
                <div className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                  msg.role === 'user' ? "bg-primary text-white" : "bg-primary-light text-primary"
                )}>
                  {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div className={cn(
                  "max-w-[80%] p-3 rounded-2xl text-sm leading-relaxed",
                  msg.role === 'user'
                    ? "bg-primary text-white rounded-tr-none"
                    : "bg-surface-muted text-text-primary rounded-tl-none border border-border"
                )}>
                  <div className={cn("prose prose-sm max-w-none break-words", msg.role === 'user' ? "prose-invert" : "prose-p:leading-relaxed prose-pre:bg-surface prose-pre:border prose-pre:border-border")}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="flex gap-3 flex-row">
                <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-primary-light text-primary">
                  <Bot size={16} />
                </div>
                <div className="max-w-[80%] p-4 rounded-2xl bg-surface-muted text-text-primary rounded-tl-none border border-border flex gap-1">
                  <div className="w-2 h-2 rounded-full bg-primary animate-bounce delay-75" />
                  <div className="w-2 h-2 rounded-full bg-primary animate-bounce delay-150" />
                  <div className="w-2 h-2 rounded-full bg-primary animate-bounce delay-300" />
                </div>
              </div>
            )}
          </div>

          <div className="p-4 bg-surface border-t border-border">
            <form onSubmit={handleSendMessage} className="relative">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask about vibration analysis, efficiency ROI, or maintenance logs..."
                className="w-full bg-surface-muted border border-border rounded-xl pl-4 pr-12 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 text-text-primary"
              />
              <button
                type="submit"
                disabled={!chatInput.trim() || isTyping}
                className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors disabled:opacity-50"
              >
                <Send size={14} />
              </button>
            </form>
          </div>
        </div>
      </div>
      <div style={{ display: 'none' }}>
        <PdfReportTemplate
          ref={pdfRef}
          machineId={activeId}
          machineName={activeMachine?.name || activeId}
          summary={reportSummary}
          healthScore={healthMetric}
          energyWaste={energyWaste}
          downtimeDays={downtimeDays}
          roiData={roiData}
          riskData={riskData}
          mechanicalHistory={mechanicalHistory}
          electricalHistory={electricalHistory}
          fftFrequencies={latestFeatures?.vibration?.fft_frequencies || []}
          fftMagnitudes={latestFeatures?.vibration?.fft_magnitudes || []}
        />
      </div>
    </div>
  );
};

export default AIAnalysis;
