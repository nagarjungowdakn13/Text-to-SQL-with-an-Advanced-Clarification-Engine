'use client';

import { useState, useEffect } from 'react';
import api from '../../lib/api';

export default function AdminPage() {
  const [provider, setProvider] = useState('mock');
  const [model, setModel] = useState('mock-model');
  const [threshold, setThreshold] = useState(0.7);
  const [maxRounds, setMaxRounds] = useState(2);
  const [maxRepairs, setMaxRepairs] = useState(3);
  const [timeout, setTimeoutSec] = useState(5);
  const [maxRows, setMaxRows] = useState(500);
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function loadSettings() {
      try {
        setLoading(true);
        const data = await api.getSettings();
        setProvider(data.default_llm_provider);
        setModel(data.default_llm_model);
        setThreshold(data.ambiguity_threshold);
        setMaxRounds(data.max_clarification_rounds);
        setMaxRepairs(data.max_repair_attempts);
        setTimeoutSec(data.query_timeout_seconds);
        setMaxRows(data.max_execution_rows);
      } catch (e) {
        console.error("Failed to load settings:", e);
      } finally {
        setLoading(false);
      }
    }
    loadSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      await api.saveSettings({
        default_llm_provider: provider,
        default_llm_model: model,
        ambiguity_threshold: threshold,
        max_clarification_rounds: maxRounds,
        max_repair_attempts: maxRepairs,
        query_timeout_seconds: timeout,
        max_execution_rows: maxRows
      });
      alert("System configurations updated successfully.");
    } catch (err: any) {
      alert(`Failed to save configurations: ${err.message || 'Error occurred.'}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-10 bg-slate-200 rounded w-1/4"></div>
        <div className="h-96 bg-slate-200 rounded-xl"></div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-3xl font-bold text-slate-800 tracking-tight">Admin settings</h2>
        <p className="text-slate-500 text-sm mt-1">Configure QueryPilot parameters, active models, ambiguity thresholds, and execution safety limits.</p>
      </div>

      <form onSubmit={handleSave} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
        <h3 className="font-bold text-slate-800 text-base border-b border-slate-100 pb-3">Engine & Security Thresholds</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Default provider */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-500 uppercase">Default LLM Provider</label>
            <select
              value={provider}
              onChange={(e) => {
                setProvider(e.target.value);
                if (e.target.value === 'mock') setModel('mock-model');
                else if (e.target.value === 'openai') setModel('gpt-4o-mini');
                else if (e.target.value === 'gemini') setModel('gemini-1.5-flash');
                else if (e.target.value === 'anthropic') setModel('claude-3-5-sonnet-20240620');
              }}
              className="w-full px-4 py-2 border border-slate-200 rounded-lg text-sm font-semibold bg-white outline-none focus:border-blue-500"
            >
              <option value="mock">Mock LLM Provider</option>
              <option value="openai">OpenAI GPT-4o</option>
              <option value="gemini">Gemini 1.5 Flash</option>
              <option value="anthropic">Claude 3.5 Sonnet</option>
            </select>
          </div>

          {/* Model Name */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-500 uppercase">Default Model Name</label>
            <input
              type="text"
              required
              disabled={provider === 'mock'}
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-4 py-2 border border-slate-200 rounded-lg text-sm font-semibold outline-none focus:border-blue-500 disabled:opacity-50"
              placeholder="Model identifier"
            />
          </div>

          {/* Ambiguity Threshold */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-500 uppercase">Ambiguity Threshold (0.0 - 1.0)</label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="flex-1 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <span className="w-12 text-center bg-slate-50 border border-slate-200 text-slate-700 font-bold px-2 py-0.5 rounded text-xs">
                {threshold.toFixed(2)}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium">Lower scores request clarification more frequently.</p>
          </div>

          {/* Max Clarification Rounds */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-500 uppercase">Max Clarification Rounds</label>
            <input
              type="number"
              min="0"
              max="5"
              required
              value={maxRounds}
              onChange={(e) => setMaxRounds(parseInt(e.target.value))}
              className="w-full px-4 py-2 border border-slate-200 rounded-lg text-sm font-semibold outline-none focus:border-blue-500"
            />
            <p className="text-[10px] text-slate-400 font-medium">Halts dialogue loops and falls back to default assumptions.</p>
          </div>

          {/* Max Repair Attempts */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-500 uppercase">Max SQL Repair Attempts</label>
            <input
              type="number"
              min="0"
              max="5"
              required
              value={maxRepairs}
              onChange={(e) => setMaxRepairs(parseInt(e.target.value))}
              className="w-full px-4 py-2 border border-slate-200 rounded-lg text-sm font-semibold outline-none focus:border-blue-500"
            />
            <p className="text-[10px] text-slate-400 font-medium">Number of retry validations if SQL query generation fails.</p>
          </div>

          {/* Query Timeout */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-500 uppercase">Query Timeout (Seconds)</label>
            <input
              type="number"
              min="1"
              max="60"
              required
              value={timeout}
              onChange={(e) => setTimeoutSec(parseInt(e.target.value))}
              className="w-full px-4 py-2 border border-slate-200 rounded-lg text-sm font-semibold outline-none focus:border-blue-500"
            />
            <p className="text-[10px] text-slate-400 font-medium">Statement timeout threshold to block infinite loops.</p>
          </div>

          {/* Max Row Limits */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-500 uppercase">Max Execution Row Count</label>
            <input
              type="number"
              min="1"
              max="1000"
              required
              value={maxRows}
              onChange={(e) => setMaxRows(parseInt(e.target.value))}
              className="w-full px-4 py-2 border border-slate-200 rounded-lg text-sm font-semibold outline-none focus:border-blue-500"
            />
            <p className="text-[10px] text-slate-400 font-medium">Caps the row return size to save payload transfer bandwidth.</p>
          </div>
        </div>

        {/* Buttons */}
        <div className="flex justify-end pt-4 border-t border-slate-100">
          <button
            type="submit"
            disabled={saving}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 border border-blue-500 text-white text-xs font-bold rounded-lg shadow-sm transition disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Configuration Parameters"}
          </button>
        </div>
      </form>
    </div>
  );
}
