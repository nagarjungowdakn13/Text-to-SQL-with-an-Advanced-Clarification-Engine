'use client';

import { useState, useEffect } from 'react';
import api from '../../lib/api';

interface ColumnMeta {
  name: string;
  data_type: string;
  is_nullable: boolean;
  comment?: string;
  sample_values?: any[];
}

interface ForeignKeyMeta {
  constrained_columns: string[];
  referred_table: string;
  referred_columns: string[];
}

interface TableMeta {
  name: string;
  comment?: string;
  columns: ColumnMeta[];
  primary_keys: string[];
  foreign_keys: ForeignKeyMeta[];
  row_count: number;
}

interface SchemaMetadata {
  tables: { [key: string]: TableMeta };
}

export default function SchemaPage() {
  const [schema, setSchema] = useState<SchemaMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchSchema = async (force: boolean = false) => {
    try {
      if (force) setRefreshing(true);
      else setLoading(true);
      
      const data = force ? await api.refreshSchema() : await api.getSchema();
      
      // If force refresh, the API returns a wrapper { status, message, schema }
      const schemaData = data.schema ? data.schema : data;
      setSchema(schemaData);
    } catch (e) {
      console.error("Failed to load schema:", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSchema();
  }, []);

  const handleRefresh = () => {
    fetchSchema(true);
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="flex justify-between">
          <div className="h-10 bg-slate-200 rounded w-1/4"></div>
          <div className="h-10 bg-slate-200 rounded w-28"></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-72 bg-slate-200 rounded-xl"></div>
          ))}
        </div>
      </div>
    );
  }

  const tables = schema ? Object.values(schema.tables) : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-slate-800 tracking-tight">Schema Explorer</h2>
          <p className="text-slate-500 text-sm mt-1">Explore current indexed database tables, columns, indexes, and primary/foreign key connections.</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-sm font-semibold rounded-lg shadow-sm flex items-center gap-2 transition disabled:opacity-50"
        >
          {refreshing ? (
            <>
              <span className="w-3 h-3 border-2 border-slate-400 border-t-transparent rounded-full animate-spin"></span>
              Refreshing...
            </>
          ) : (
            <>🔄 Refresh Cache</>
          )}
        </button>
      </div>

      {/* Grid of Tables */}
      {tables.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-400 text-sm font-medium shadow-sm">
          No database tables could be extracted. Run database migrations or verify target DB connections.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {tables.map((table) => (
            <div key={table.name} className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col hover:shadow-md transition-shadow duration-200">
              {/* Table header bar */}
              <div className="px-6 py-4 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg flex items-center gap-1.5">
                    🗂️ {table.name}
                  </h3>
                  {table.comment && (
                    <p className="text-[11px] text-slate-500 font-medium mt-0.5">{table.comment}</p>
                  )}
                </div>
                <span className="px-2.5 py-0.5 bg-blue-50 text-blue-700 border border-blue-100 rounded text-xs font-bold shrink-0">
                  Rows: {table.row_count}
                </span>
              </div>

              {/* Columns List */}
              <div className="flex-1 p-6 space-y-4">
                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Columns Schema</span>
                  <div className="border border-slate-100 rounded-lg overflow-hidden bg-slate-50/50">
                    <table className="min-w-full divide-y divide-slate-100 text-xs text-left">
                      <thead className="bg-slate-100/50 font-bold text-slate-500">
                        <tr>
                          <th className="px-4 py-2">Column</th>
                          <th className="px-4 py-2">Type</th>
                          <th className="px-4 py-2">Constraint</th>
                          <th className="px-4 py-2">Sample values</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-medium text-slate-600">
                        {table.columns.map((col) => {
                          const isPk = table.primary_keys.includes(col.name);
                          const isFk = table.foreign_keys.some(fk => fk.constrained_columns.includes(col.name));
                          
                          return (
                            <tr key={col.name} className="hover:bg-white transition-colors">
                              <td className="px-4 py-2.5 font-semibold text-slate-800 flex items-center gap-1">
                                {isPk && <span className="text-amber-500" title="Primary Key">🔑</span>}
                                {col.name}
                              </td>
                              <td className="px-4 py-2.5 font-mono text-[10px] text-slate-400">{col.data_type}</td>
                              <td className="px-4 py-2.5">
                                {isPk && <span className="text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.2 rounded font-bold uppercase tracking-wider text-[8px]">PK</span>}
                                {isFk && <span className="text-blue-700 bg-blue-50 border border-blue-200 px-1.5 py-0.2 rounded font-bold uppercase tracking-wider text-[8px] ml-1">FK</span>}
                                {!col.is_nullable && !isPk && <span className="text-slate-400 font-medium">NOT NULL</span>}
                              </td>
                              <td className="px-4 py-2.5 font-mono text-[10px] text-slate-400 truncate max-w-[150px]" title={col.sample_values?.join(', ')}>
                                {col.sample_values && col.sample_values.length > 0 
                                  ? col.sample_values.join(', ') 
                                  : '-'}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Foreign Key Connections list */}
                {table.foreign_keys.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Relations Graph Linkages</span>
                    <ul className="text-xs font-semibold text-slate-600 space-y-1.5">
                      {table.foreign_keys.map((fk, idx) => (
                        <li key={idx} className="flex items-center gap-1.5 bg-blue-50/50 border border-blue-100/50 rounded-lg px-3 py-2 text-blue-800">
                          <span>🔗</span>
                          <span>
                            ({fk.constrained_columns.join(', ')}) maps to 
                            <span className="font-bold text-blue-900"> {fk.referred_table}</span>
                            ({fk.referred_columns.join(', ')})
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
