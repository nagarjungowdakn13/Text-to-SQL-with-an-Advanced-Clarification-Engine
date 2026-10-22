'use client';

import { useState, useEffect } from 'react';
import api from '../../lib/api';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend
} from 'recharts';

interface Message {
  type: 'user' | 'system' | 'clarification';
  text: string;
  options?: string[];
  sql?: string;
  explanation?: string;
  insights?: string[];
  anomalies?: string[];
  assumptions?: string[];
  columns?: string[];
  rows?: any[];
  latency?: number;
  confidence?: number;
  isError?: boolean;
}

export default function WorkspacePage() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>(undefined);
  const [provider, setProvider] = useState('mock');
  const [model, setModel] = useState('mock-model');
  const [availableProviders, setAvailableProviders] = useState<{ [key: string]: string }>({
    mock: 'Mock LLM Provider',
    openai: 'OpenAI GPT-4o',
    gemini: 'Gemini 1.5 Flash',
    anthropic: 'Claude 3.5 Sonnet'
  });

  // Automatically start with a welcome instruction message
  useEffect(() => {
    setMessages([
      {
        type: 'system',
        text: "Welcome to QueryPilot Workspace! Ask me any question about your e-commerce data (e.g. 'Show our total revenue' or 'Who is our best customer?'). I will analyze your intent, check for ambiguities, query the database safely, and explain the findings."
      }
    ]);
  }, []);

  const handleQuerySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    const userMsg = question;
    setQuestion('');
    setLoading(true);

    // Append user question
    setMessages(prev => [...prev, { type: 'user', text: userMsg }]);

    try {
      const response = await api.analyze(userMsg, activeSessionId, provider, model);
      processApiResponse(response);
    } catch (err: any) {
      setMessages(prev => [...prev, {
        type: 'system',
        text: `Pipeline Error: ${err.message || 'An unexpected error occurred.'}`,
        isError: true
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleClarificationChoice = async (choice: string) => {
    if (!activeSessionId) return;
    setLoading(true);

    // Append user choice
    setMessages(prev => [...prev, { type: 'user', text: `Selected: ${choice}` }]);

    try {
      const response = await api.respond(activeSessionId, choice, provider, model);
      processApiResponse(response);
    } catch (err: any) {
      setMessages(prev => [...prev, {
        type: 'system',
        text: `Pipeline Error: ${err.message || 'An unexpected error occurred.'}`,
        isError: true
      }]);
    } finally {
      setLoading(false);
    }
  };

  const processApiResponse = (res: any) => {
    if (res.status === 'clarifying') {
      setActiveSessionId(res.session_id);
      setMessages(prev => [...prev, {
        type: 'clarification',
        text: res.clarification_question,
        options: res.options
      }]);
    } else if (res.status === 'success') {
      setActiveSessionId(undefined); // Reset session on success
      setMessages(prev => [...prev, {
        type: 'system',
        text: `Query Executed Successfully!`,
        sql: res.sql,
        explanation: res.explanation,
        insights: res.insights,
        anomalies: res.anomalies,
        assumptions: res.assumptions,
        columns: res.columns,
        rows: res.rows,
        latency: res.execution_time_ms,
        confidence: res.confidence
      }]);
    } else if (res.status === 'failed') {
      setActiveSessionId(undefined);
      setMessages(prev => [...prev, {
        type: 'system',
        text: res.error || 'Query failed execution.',
        sql: res.sql,
        isError: true
      }]);
    }
  };

  // Helper to detect if records are chartable, and extract the series data
  const getChartData = (columns: string[] | undefined, rows: any[] | undefined) => {
    if (!columns || !rows || rows.length === 0) return null;

    // Find a numeric column to serve as values
    const valueCol = columns.find(col => {
      const sample = rows[0][col];
      return typeof sample === 'number' || (typeof sample === 'string' && !isNaN(Number(sample)));
    });

    // Find a column to serve as labels (categorical string names)
    const labelCol = columns.find(col => {
      if (col === valueCol) return false;
      const sample = rows[0][col];
      return typeof sample === 'string' && isNaN(Number(sample));
    }) || columns[0];

    if (!valueCol || !labelCol) return null;

    const formattedData = rows.map(row => ({
      name: row[labelCol] || 'Unknown',
      value: Number(row[valueCol])
    }));

    return {
      data: formattedData,
      xKey: 'name',
      yKey: 'value',
      yName: valueCol.replace(/_/g, ' ').toUpperCase()
    };
  };

  return (
    <div className="flex flex-col h-[calc(100vh-10rem)] max-w-6xl mx-auto space-y-6">
      {/* Top Controls: Provider Selection */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
        <div>
          <h3 className="font-bold text-slate-800 text-sm">Disambiguation Workspace</h3>
          <p className="text-slate-500 text-xs mt-0.5">Toggle LLM model engines to compare Text-to-SQL logic.</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={provider}
            onChange={(e) => {
              setProvider(e.target.value);
              if (e.target.value === 'mock') setModel('mock-model');
              else if (e.target.value === 'openai') setModel('gpt-4o-mini');
              else if (e.target.value === 'gemini') setModel('gemini-1.5-flash');
              else if (e.target.value === 'anthropic') setModel('claude-3-5-sonnet-20240620');
            }}
            className="text-xs font-semibold px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 outline-none"
          >
            {Object.entries(availableProviders).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={provider === 'mock'}
            className="text-xs font-semibold px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 outline-none w-44 disabled:opacity-50"
            placeholder="Model identifier"
          />
        </div>
      </div>

      {/* Main chat dialogue scroll box */}
      <div className="flex-1 bg-white border border-slate-200 rounded-xl shadow-sm flex flex-col min-h-0">
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex flex-col ${
                msg.type === 'user' ? 'items-end' : 'items-start'
              }`}
            >
              {/* Message Bubble */}
              <div
                className={`max-w-2xl px-5 py-3 rounded-2xl shadow-sm border ${
                  msg.type === 'user'
                    ? 'bg-blue-600 border-blue-500 text-white rounded-tr-none'
                    : msg.isError
                    ? 'bg-red-50 border-red-200 text-red-800 rounded-tl-none'
                    : 'bg-slate-50 border-slate-100 text-slate-800 rounded-tl-none'
                }`}
              >
                <div className="text-sm font-medium leading-relaxed">{msg.text}</div>

                {/* Clarification Choices Cards */}
                {msg.type === 'clarification' && msg.options && (
                  <div className="grid grid-cols-1 gap-2.5 mt-4">
                    {msg.options.map((opt, oIdx) => (
                      <button
                        key={oIdx}
                        onClick={() => handleClarificationChoice(opt)}
                        disabled={loading}
                        className="text-left w-full px-4 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-xl text-xs font-bold hover:bg-slate-100 hover:border-slate-300 transition-colors duration-150 shadow-sm"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Success metadata payload (SQL, Data, Explanations, Graphs) */}
              {msg.type === 'system' && msg.sql && !msg.isError && (
                <div className="w-full max-w-4xl bg-slate-50 border border-slate-200 rounded-xl p-5 mt-4 space-y-5">
                  
                  {/* Title & metrics bar */}
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Plan Metadata</span>
                    <div className="flex gap-3 text-[10px] font-bold text-slate-500">
                      <span className="px-2 py-0.5 bg-slate-200 rounded">Latency: {msg.latency?.toFixed(1)}ms</span>
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded">Confidence: {(msg.confidence || 0) * 100}%</span>
                    </div>
                  </div>

                  {/* Assumptions */}
                  {msg.assumptions && msg.assumptions.length > 0 && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 flex items-start gap-2">
                      <span className="text-sm">⚠️</span>
                      <div>
                        <span className="font-bold">Assumptions made:</span>
                        <ul className="list-disc pl-4 mt-1 font-medium space-y-0.5">
                          {msg.assumptions.map((asm, aIdx) => (
                            <li key={aIdx}>{asm}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}

                  {/* Generated SQL Monospace codeblock */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-bold text-slate-500 uppercase">
                      <span>PostgreSQL query</span>
                      <button
                        onClick={() => {
                          if (msg.sql) {
                            navigator.clipboard.writeText(msg.sql);
                            alert("SQL copied to clipboard!");
                          }
                        }}
                        className="text-[10px] text-blue-600 hover:text-blue-700 bg-white border border-slate-200 px-2 py-0.5 rounded shadow-sm transition-all"
                      >
                        Copy SQL
                      </button>
                    </div>
                    <pre className="bg-slate-900 text-slate-100 font-mono text-xs p-4 rounded-lg overflow-x-auto select-all leading-normal border border-slate-950 shadow-inner">
                      {msg.sql}
                    </pre>
                  </div>

                  {/* Natural Language explanation summarization */}
                  {msg.explanation && (
                    <div className="space-y-2 text-sm bg-white border border-slate-200 rounded-lg p-4">
                      <h4 className="font-bold text-slate-800 border-b border-slate-100 pb-1.5">Result Explanation</h4>
                      <p className="text-slate-700 leading-relaxed font-medium">{msg.explanation}</p>
                      
                      {msg.insights && msg.insights.length > 0 && (
                        <div className="mt-3">
                          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Key Insights</span>
                          <ul className="list-disc pl-5 mt-1 text-xs text-slate-600 font-medium space-y-1">
                            {msg.insights.map((ins, iIdx) => (
                              <li key={iIdx}>{ins}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Results Data Grid & Dynamic Chart */}
                  {msg.columns && msg.rows && msg.rows.length > 0 && (
                    <div className="space-y-4">
                      <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wider">Retrieved Dataset ({msg.rows.length} rows)</h4>
                      
                      {/* Dynamic charts using recharts */}
                      {(() => {
                        const chartMeta = getChartData(msg.columns, msg.rows);
                        if (!chartMeta) return null;
                        return (
                          <div className="bg-white border border-slate-200 rounded-lg p-4 h-64 shadow-sm">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={chartMeta.data}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                                <YAxis tick={{ fontSize: 10 }} />
                                <Tooltip />
                                <Bar dataKey="value" name={chartMeta.yName} fill="#2563eb" radius={[4, 4, 0, 0]} />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        );
                      })()}

                      {/* Interactive scrollable data table */}
                      <div className="overflow-x-auto border border-slate-200 rounded-lg bg-white shadow-sm">
                        <table className="min-w-full divide-y divide-slate-200 text-xs">
                          <thead className="bg-slate-50 font-bold text-slate-600 text-left">
                            <tr>
                              {msg.columns.map((col) => (
                                <th key={col} className="px-4 py-2.5">{col}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 text-slate-700 font-medium">
                            {msg.rows.map((row, rIdx) => (
                              <tr key={rIdx} className="hover:bg-slate-50">
                                {msg.columns!.map((col) => (
                                  <td key={col} className="px-4 py-2.5 truncate max-w-xs">{row[col]}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {/* Loader */}
          {loading && (
            <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold">
              <span className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></span>
              <span className="w-2 h-2 bg-blue-600 rounded-full animate-bounce delay-75"></span>
              <span className="w-2 h-2 bg-blue-600 rounded-full animate-bounce delay-150"></span>
              <span>QueryPilot is planning SQL...</span>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <form onSubmit={handleQuerySubmit} className="p-4 border-t border-slate-200 bg-slate-50 rounded-b-xl flex gap-3">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
            placeholder={
              activeSessionId 
                ? "Provide clarification (choose card above or write text)..." 
                : "Type your data question (e.g. 'Show active users in NY')..."
            }
            className="flex-1 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-semibold outline-none shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="px-5 py-2.5 bg-blue-600 border border-blue-500 text-white rounded-xl text-sm font-bold shadow hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            Submit
          </button>
        </form>
      </div>
    </div>
  );
}
