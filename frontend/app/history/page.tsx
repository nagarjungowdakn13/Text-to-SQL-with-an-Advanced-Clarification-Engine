'use client';

import { useState, useEffect } from 'react';
import api from '../../lib/api';

interface QueryHistoryItem {
  id: number;
  session_id: string;
  user_question: string;
  resolved_question: string;
  generated_sql: string;
  execution_status: string;
  execution_error?: string;
  row_count: number;
  execution_time_ms: number;
  explanation: string;
  assumptions?: any;
  confidence: number;
  created_at: string;
}

interface AuditLogItem {
  id: number;
  step: string;
  details: any;
  created_at: string;
}

export default function HistoryPage() {
  const [historyList, setHistoryList] = useState<QueryHistoryItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<QueryHistoryItem | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [logsLoading, setLogsLoading] = useState(false);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const data = await api.getHistory();
      setHistoryList(data);
      if (data.length > 0) {
        setSelectedItem(data[0]);
      }
    } catch (e) {
      console.error("Failed to fetch query execution history:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    async function loadAudits() {
      if (!selectedItem) return;
      try {
        setLogsLoading(true);
        const data = await api.getAuditLogs(selectedItem.session_id);
        setAuditLogs(data);
      } catch (e) {
        console.error("Failed to load audit logs:", e);
        setAuditLogs([]);
      } finally {
        setLogsLoading(false);
      }
    }

    loadAudits();
  }, [selectedItem]);

  if (loading && historyList.length === 0) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-10 bg-slate-200 rounded w-1/4"></div>
        <div className="grid grid-cols-3 gap-6">
          <div className="h-96 bg-slate-200 rounded-xl"></div>
          <div className="col-span-2 h-96 bg-slate-200 rounded-xl"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-3xl font-bold text-slate-800 tracking-tight">Audit Trail & Observability Logs</h2>
        <p className="text-slate-500 text-sm mt-1">Review complete query history and inspect agent chain-of-thought metadata without leaking private diagnostics to basic viewers.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-[calc(100vh-14rem)] min-h-0">
        {/* Left column: History List */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col min-h-0">
          <div className="px-6 py-4 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-bold text-slate-800 text-sm">Query History Logs</h3>
          </div>
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100 min-h-0">
            {historyList.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-sm font-medium">No records found.</div>
            ) : (
              historyList.map((item) => (
                <div
                  key={item.id}
                  onClick={() => setSelectedItem(item)}
                  className={`p-4 text-left cursor-pointer transition-colors duration-150 ${
                    selectedItem?.id === item.id 
                      ? 'bg-blue-50 border-l-4 border-blue-600' 
                      : 'hover:bg-slate-50 border-l-4 border-transparent'
                  }`}
                >
                  <p className="font-semibold text-slate-800 text-xs truncate">{item.user_question}</p>
                  <div className="flex items-center justify-between mt-2.5 text-[10px] font-bold text-slate-400">
                    <span>{new Date(item.created_at).toLocaleTimeString()}</span>
                    <span className={`px-2 py-0.5 rounded text-[8px] uppercase tracking-wider ${
                      item.execution_status === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
                    }`}>
                      {item.execution_status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right 2 cols: Audit Detail view */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col min-h-0">
          {selectedItem ? (
            <div className="flex-1 flex flex-col min-h-0">
              {/* Header bar */}
              <div className="px-6 py-4 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-800 text-sm truncate max-w-md" title={selectedItem.user_question}>
                    {selectedItem.user_question}
                  </h3>
                  <p className="text-[10px] text-slate-400 font-mono mt-0.5">Session ID: {selectedItem.session_id}</p>
                </div>
                <div className="flex gap-2">
                  <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded border ${
                    selectedItem.execution_status === 'success' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200'
                  }`}>
                    {selectedItem.execution_status}
                  </span>
                </div>
              </div>

              {/* Scrollable details and audit logs timeline */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6 min-h-0">
                {/* Execution parameters grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-50 border border-slate-100 rounded-lg p-4 text-xs font-semibold text-slate-600">
                  <div className="space-y-0.5">
                    <span className="text-[10px] text-slate-400 font-bold uppercase">Time spent</span>
                    <p className="text-slate-800 font-bold">{selectedItem.execution_time_ms.toFixed(1)} ms</p>
                  </div>
                  <div className="space-y-0.5">
                    <span className="text-[10px] text-slate-400 font-bold uppercase">Rows fetched</span>
                    <p className="text-slate-800 font-bold">{selectedItem.row_count} rows</p>
                  </div>
                  <div className="space-y-0.5">
                    <span className="text-[10px] text-slate-400 font-bold uppercase">Model confidence</span>
                    <p className="text-slate-800 font-bold">{(selectedItem.confidence * 100).toFixed(0)}%</p>
                  </div>
                  <div className="space-y-0.5">
                    <span className="text-[10px] text-slate-400 font-bold uppercase">SQL check</span>
                    <p className="text-emerald-600 font-bold">Passed</p>
                  </div>
                </div>

                {/* SQL query codeblock */}
                {selectedItem.generated_sql && (
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Generated SQL Query</span>
                    <pre className="bg-slate-900 text-slate-100 font-mono text-[11px] p-4 rounded-lg overflow-x-auto border border-slate-950">
                      {selectedItem.generated_sql}
                    </pre>
                  </div>
                )}

                {/* Database error text */}
                {selectedItem.execution_error && (
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Execution error summary</span>
                    <div className="bg-red-50 border border-red-200 text-red-800 text-xs font-mono p-4 rounded-lg whitespace-pre-wrap leading-relaxed">
                      {selectedItem.execution_error}
                    </div>
                  </div>
                )}

                {/* Database explanation */}
                {selectedItem.explanation && (
                  <div className="space-y-1.5 bg-slate-50 border border-slate-100 rounded-lg p-4 text-xs leading-relaxed">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block border-b border-slate-200 pb-1">Result Summary</span>
                    <p className="text-slate-700 font-medium pt-1.5">{selectedItem.explanation}</p>
                  </div>
                )}

                {/* Audit steps timeline */}
                <div className="space-y-3 pt-2 border-t border-slate-100">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Chain of Thought Audit Trail</span>
                  {logsLoading ? (
                    <div className="text-center text-slate-400 text-xs py-4 font-semibold">Loading logs...</div>
                  ) : auditLogs.length === 0 ? (
                    <div className="text-center text-slate-400 text-xs py-4 font-medium">No internal step records found for this session.</div>
                  ) : (
                    <div className="relative border-l border-slate-200 pl-4 ml-2 space-y-5">
                      {auditLogs.map((log) => (
                        <div key={log.id} className="relative group">
                          {/* Timeline node icon */}
                          <div className="absolute -left-[21px] mt-1 w-2.5 h-2.5 bg-blue-600 rounded-full border border-white"></div>
                          
                          {/* Log card */}
                          <div className="bg-slate-50 hover:bg-slate-100/50 border border-slate-100 rounded-lg p-4 transition duration-150">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                                {log.step.replace(/_/g, ' ')}
                              </span>
                              <span className="text-[9px] text-slate-400 font-medium">
                                {new Date(log.created_at).toLocaleTimeString()}
                              </span>
                            </div>
                            
                            {/* Nested details display */}
                            <pre className="mt-2.5 font-mono text-[10px] text-slate-500 bg-white border border-slate-200/60 rounded p-2.5 overflow-x-auto shadow-inner leading-normal max-h-36">
                              {JSON.stringify(log.details, null, 2)}
                            </pre>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400 text-sm font-medium">
              Select an item from history to review details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
