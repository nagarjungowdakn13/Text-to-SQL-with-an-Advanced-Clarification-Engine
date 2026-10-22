'use client';

import { useState, useEffect } from 'react';
import api from '../../lib/api';

interface SemanticMapping {
  id: number;
  term: string;
  category: string;
  definition: string;
  sql_fragment: string;
}

export default function SemanticsPage() {
  const [terms, setTerms] = useState<SemanticMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [role, setRole] = useState('viewer');

  // Form states
  const [termName, setTermName] = useState('');
  const [category, setCategory] = useState('metric');
  const [definition, setDefinition] = useState('');
  const [sqlFragment, setSqlFragment] = useState('');

  const loadSemantics = async () => {
    try {
      setLoading(true);
      const data = await api.getSemantics();
      setTerms(data);
      
      const sessionData = await api.getSettings().catch(() => ({}));
      // User role
      setRole('admin'); // Defaulting admin context for this tab
    } catch (e) {
      console.error("Failed to load semantic mapping definitions:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSemantics();
  }, []);

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!termName.trim() || !sqlFragment.trim()) return;

    try {
      setLoading(true);
      await api.saveSemantic(
        termName.trim().toLowerCase(),
        category,
        sqlFragment.trim(),
        definition.trim()
      );
      // Reset form
      setTermName('');
      setDefinition('');
      setSqlFragment('');
      setEditing(false);
      // Reload mappings
      await loadSemantics();
    } catch (err: any) {
      alert(`Failed to save semantic mapping: ${err.message || 'Error occurred.'}`);
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this business semantic term?")) return;
    try {
      setLoading(true);
      await api.deleteSemantic(id);
      await loadSemantics();
    } catch (err: any) {
      alert(`Failed to delete mapping: ${err.message || 'Error occurred.'}`);
      setLoading(false);
    }
  };

  if (loading && terms.length === 0) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-10 bg-slate-200 rounded w-1/4"></div>
        <div className="h-44 bg-slate-200 rounded-xl"></div>
        <div className="h-44 bg-slate-200 rounded-xl"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-slate-800 tracking-tight">Business Semantic Layer</h2>
          <p className="text-slate-500 text-sm mt-1">Configure business definitions and glossary terms. The SQL generator automatically compiles these metrics at execution time.</p>
        </div>
        <button
          onClick={() => setEditing(!editing)}
          className="px-4 py-2 bg-blue-600 border border-blue-500 hover:bg-blue-700 text-white text-sm font-bold rounded-lg shadow-sm transition"
        >
          {editing ? "Cancel Edit" : "➕ Define Glossary Term"}
        </button>
      </div>

      {/* Editor Panel Inline */}
      {editing && (
        <form onSubmit={handleAddSubmit} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 className="font-bold text-slate-800 text-base">New Semantic Translation</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Term Name */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-500 uppercase">Business term name</label>
              <input
                type="text"
                required
                value={termName}
                onChange={(e) => setTermName(e.target.value)}
                placeholder="e.g., active customer, profit, revenue"
                className="w-full px-4 py-2 border border-slate-200 rounded-lg text-sm font-semibold outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
              />
            </div>

            {/* Category selection */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-500 uppercase">Category type</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-4 py-2 border border-slate-200 rounded-lg text-sm font-semibold outline-none bg-white focus:border-blue-500"
              >
                <option value="metric">Metric (aggregation formulas)</option>
                <option value="dimension">Dimension (attributes)</option>
                <option value="business_rule">Business Rule (filter expressions)</option>
              </select>
            </div>
          </div>

          {/* Definition */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-500 uppercase">Business definition (comment)</label>
            <input
              type="text"
              value={definition}
              onChange={(e) => setDefinition(e.target.value)}
              placeholder="e.g., A customer who has placed an order within the last 90 days."
              className="w-full px-4 py-2 border border-slate-200 rounded-lg text-sm font-semibold outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
            />
          </div>

          {/* SQL Fragment */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-500 uppercase">SQL fragment formula</label>
            <textarea
              required
              rows={2}
              value={sqlFragment}
              onChange={(e) => setSqlFragment(e.target.value)}
              placeholder="e.g., SUM(order_items.quantity * order_items.unit_price) OR customers.last_order_date >= NOW() - INTERVAL '90 days'"
              className="w-full px-4 py-2 border border-slate-200 rounded-lg text-sm font-semibold font-mono outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 bg-blue-600 border border-blue-500 text-white text-xs font-bold rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
          >
            Save translation mapping
          </button>
        </form>
      )}

      {/* Semantic mappings glossary list */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-100">
          <h3 className="font-bold text-slate-800">Business Glossary Terms</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
            <thead className="bg-slate-50 font-bold text-slate-600 uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3.5">Business term</th>
                <th className="px-6 py-3.5">Category</th>
                <th className="px-6 py-3.5">Business definition</th>
                <th className="px-6 py-3.5">SQL formula fragment</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700 font-semibold">
              {terms.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-400 font-medium">
                    No business terms defined. Define terms to assist SQL generation mappings.
                  </td>
                </tr>
              ) : (
                terms.map((term) => (
                  <tr key={term.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 font-bold text-slate-800">{term.term}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        term.category === 'metric' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                        term.category === 'dimension' ? 'bg-purple-50 text-purple-700 border border-purple-200' :
                        'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}>
                        {term.category.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-500 font-medium max-w-xs truncate" title={term.definition}>{term.definition || '-'}</td>
                    <td className="px-6 py-4 font-mono text-[11px] text-slate-600 bg-slate-50/50">{term.sql_fragment}</td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleDelete(term.id)}
                        disabled={loading}
                        className="text-red-600 hover:text-red-700 font-bold hover:underline transition"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
