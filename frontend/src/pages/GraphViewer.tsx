import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
// @ts-ignore
import dagre from 'cytoscape-dagre';
import { FiLoader, FiAlertCircle, FiShield } from 'react-icons/fi';
import clsx from 'clsx';
import { getGraph, getTaintGraph, GraphResponse, GraphNode } from '../services/api';

cytoscape.use(dagre);

type Layer = 'ALL' | 'AST' | 'CFG' | 'DFG' | 'TAINT';

const LAYER_COLORS: Record<string, string> = {
  METHOD:            '#6366f1',
  CALL:              '#8b5cf6',
  IDENTIFIER:        '#06b6d4',
  LITERAL:           '#10b981',
  CONTROL_STRUCTURE: '#f59e0b',
  RETURN:            '#f43f5e',
  PARAM:             '#64748b',
  BLOCK:             '#94a3b8',
  LOCAL:             '#a78bfa',
  UNKNOWN:           '#cbd5e1',
};

const EDGE_COLORS: Record<string, string> = {
  AST: '#a5b4fc',
  CFG: '#6ee7b7',
  DFG: '#fde68a',
};

function nodeColor(label?: string): string {
  return LAYER_COLORS[label ?? 'UNKNOWN'] ?? LAYER_COLORS.UNKNOWN;
}

export default function GraphViewer({ taintMode = false }: { taintMode?: boolean }) {
  const { jobId, taintJobId } = useParams<{ jobId?: string; taintJobId?: string }>();
  const [data, setData] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [layer, setLayer] = useState<Layer>(taintMode ? 'TAINT' : 'ALL');
  const [selected, setSelected] = useState<GraphNode & Record<string, any> | null>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    const id = taintMode ? taintJobId : jobId;
    if (!id) return;
    
    const fetcher = taintMode ? getTaintGraph : getGraph;

    fetcher(id)
      .then(setData)
      .catch((err) => {
          console.error(err);
          setError('Graph not available. Ensure the job has completed.');
      })
      .finally(() => setLoading(false));
  }, [jobId, taintJobId, taintMode]);

  const elements = React.useMemo(() => {
    if (!data) return [];
    const nodes = data.nodes.map((n: Record<string, any>) => {
      // Taint feature logic
      let bg = nodeColor(n.label);
      let borderColor = '#ffffff';
      let borderWidth = 2;
      let labelSuffix = '';

      if (layer === 'TAINT') {
        if (n.is_source) {
          borderColor = '#22c55e'; // Green boundary
          borderWidth = 4;
        }
        if (n.is_sink) {
          bg = '#ef4444'; // Red fill
        } else if (n.is_tainted) {
          bg = '#eab308'; // Yellow fill
        }
        if (n.is_sanitized) labelSuffix = ' 🛡️';
      }

      return {
        data: {
          id: n.id,
          label: (n.label ?? 'NODE') + (n.line_number ? `:${n.line_number}` : '') + labelSuffix,
          nodeLabel: n.label,
          code: n.code ?? '',
          lineNumber: n.line_number,
          filename: n.filename,
          layers: n.layers ?? [],
          color: bg,
          borderColor,
          borderWidth,
          ...n // Pass all arbitrary attrs (is_source, is_sink, etc.)
        },
        classes: n.on_attack_path && layer === 'TAINT' ? 'attack-path' : '',
      }
    });

    const edges = data.edges
      .filter((e: Record<string, any>) => {
        if (layer === 'ALL') return true;
        if (layer === 'TAINT') return (e.layer ?? e.label) === 'REACHING_DEF' || (e.layer ?? e.label) === 'DFG';
        return (e.layer ?? e.label) === layer;
      })
      .map((e: Record<string, any>, i: number) => {
        let edgeColor = EDGE_COLORS[e.layer ?? e.label ?? 'AST'] ?? '#cbd5e1';
        let width = 1.5;
        let opacity = 0.7;

        if (layer === 'TAINT' && e.on_attack_path) {
          edgeColor = '#9333ea'; // Purple
          width = 3;
          opacity = 1.0;
        }

        return {
          data: {
            id: `e-${i}`,
            source: e.source,
            target: e.target,
            label: e.label ?? '',
            layer: e.layer ?? e.label ?? 'AST',
            color: edgeColor,
            width,
            opacity,
            ...e
          },
          classes: e.on_attack_path && layer === 'TAINT' ? 'attack-path' : '',
        }
      });

    return [...nodes, ...edges];
  }, [data, layer]);

  const stylesheet: cytoscape.StylesheetStyle[] = [
    {
      selector: 'node',
      style: {
        'background-color': 'data(color)' as unknown as string,
        label: 'data(label)',
        color: '#1e293b',
        'font-size': 9,
        'text-valign': 'bottom',
        'text-halign': 'center',
        width: 32,
        height: 32,
        'border-width': 'data(borderWidth)' as unknown as number,
        'border-color': 'data(borderColor)' as unknown as string,
        'text-margin-y': 4,
        'text-outline-color': 'white',
        'text-outline-width': 1,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: 'node:selected',
      style: {
        'border-color': '#000000',
        'border-width': 4,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: 'edge',
      style: {
        'line-color': 'data(color)' as unknown as string,
        'target-arrow-color': 'data(color)' as unknown as string,
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        width: 'data(width)' as unknown as number,
        opacity: 'data(opacity)' as unknown as number,
        'font-size': 8,
        label: 'data(label)',
        color: '#64748b',
        'text-outline-color': 'white',
        'text-outline-width': 1,
      } as unknown as cytoscape.Css.Edge,
    },
    {
      selector: 'edge.attack-path',
      style: {
        'z-index': 100,
        'line-style': 'dashed',
        'line-dash-pattern': [6, 3],
      } as unknown as cytoscape.Css.Edge
    }
  ];

  return (
    <div className="flex flex-col h-full gap-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">
            {taintMode ? 'Security Graph Viewer' : 'Graph Viewer'}
          </h1>
          <p className="text-sm text-surface-400 font-mono mt-0.5">{taintMode ? taintJobId : jobId}</p>
        </div>

        {/* Layer toggle */}
        <div className="flex gap-2 bg-surface-100 p-1 rounded-xl border border-surface-200">
          {(['ALL', 'AST', 'CFG', 'DFG', 'TAINT'] as Layer[]).map(l => {
            if (l === 'TAINT' && !taintMode) return null; // Only show TAINT if in taint mode
            return (
              <button
                key={l}
                onClick={() => setLayer(l)}
                className={clsx(
                  'px-4 py-1.5 rounded-lg text-sm font-semibold transition-all',
                  layer === l
                    ? 'bg-primary-600 text-white shadow-glow'
                    : 'text-surface-600 hover:bg-surface-200 hover:text-surface-900',
                )}
              >
                {l}
              </button>
            );
          })}
        </div>
      </div>

      {loading && (
        <div className="flex-1 flex items-center justify-center gap-3 text-primary-500">
          <FiLoader className="animate-spin w-6 h-6" />
          <span>Loading graph…</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          <FiAlertCircle className="w-5 h-5 shrink-0" />
          {error}
        </div>
      )}

      {data && !loading && (
        <div className="flex gap-4 flex-1 min-h-[600px]">
          {/* Graph canvas */}
          <div className="flex-1 rounded-xl border border-surface-200 overflow-hidden bg-surface-900/5">
            <CytoscapeComponent
              elements={elements}
              stylesheet={stylesheet}
              layout={{ name: 'dagre', rankDir: 'TB', nodeSep: 40, rankSep: 70 } as cytoscape.LayoutOptions}
              style={{ width: '100%', height: '100%' }}
              cy={cy => {
                cyRef.current = cy;
                cy.on('tap', 'node', evt => {
                  const nodeData = evt.target.data();
                  setSelected(nodeData);
                });
                cy.on('tap', evt => {
                  if (evt.target === cy) setSelected(null);
                });
              }}
            />
          </div>

          {/* Node detail panel */}
          {selected && (
            <div className="w-80 rounded-xl border border-surface-200 bg-white p-5 animate-slide-up shrink-0 shadow-lg flex flex-col">
              <h3 className="font-bold text-surface-900 mb-4 border-b pb-2">Node Inspector</h3>
              
              <div className="space-y-3 text-sm flex-1 overflow-y-auto">
                <div><span className="text-surface-400 font-medium block">ID</span><span className="font-mono text-xs text-surface-700 break-all">{selected.id}</span></div>
                <div><span className="text-surface-400 font-medium block">Type</span><span className="font-bold px-2 py-0.5 rounded text-xs text-white" style={{ backgroundColor: nodeColor(selected.nodeLabel) }}>{selected.nodeLabel}</span></div>
                
                {selected.code && (
                  <div>
                    <span className="text-surface-400 font-medium block mb-1">Code snippet</span>
                    <div className="font-mono text-[11px] bg-surface-900 text-surface-50 p-3 rounded-lg overflow-x-auto whitespace-pre">
                      {selected.code}
                    </div>
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-2">
                  {selected.lineNumber && <div><span className="text-surface-400 font-medium block">Line</span><span>{selected.lineNumber}</span></div>}
                  {selected.filename && <div><span className="text-surface-400 font-medium block">File</span><span className="text-xs truncate" title={selected.filename}>{selected.filename.split('/').pop()}</span></div>}
                </div>

                {/* Taint specific properties */}
                {taintMode && (
                  <div className="mt-4 pt-4 border-t border-surface-100 space-y-2">
                    <h4 className="font-semibold text-primary-900 flex items-center gap-1"><FiShield /> Security Attributes</h4>
                    
                    {selected.is_source && (
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        <span className="font-medium text-green-700 text-xs uppercase">Taint Source</span>
                        <span className="text-xs text-surface-500">({selected.source_category})</span>
                      </div>
                    )}
                    
                    {selected.is_sink && (
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-red-500"></span>
                        <span className="font-medium text-red-700 text-xs uppercase">Taint Sink</span>
                        <span className="text-xs text-surface-500">({selected.sink_category})</span>
                      </div>
                    )}
                    
                    {!selected.is_sink && selected.is_tainted && (
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
                        <span className="font-medium text-yellow-700 text-xs uppercase">Tainted Node</span>
                      </div>
                    )}
                    
                    {selected.is_sanitized && (
                      <div className="flex items-center gap-2 mt-1">
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                        <span className="font-medium text-emerald-700 text-xs uppercase">Sanitizer (Safe)</span>
                      </div>
                    )}

                    {selected.on_attack_path && (
                      <div className="mt-2 text-xs font-semibold text-purple-700 bg-purple-50 p-2 rounded-lg border border-purple-200">
                        ⚡ Part of an active attack path
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      {data && (
        <div className="flex justify-between items-center bg-white p-3 rounded-xl border border-surface-200">
          <div className="flex gap-4 flex-wrap text-sm text-surface-600 font-medium">
            {Object.entries(EDGE_COLORS).map(([k, c]) => (
              <span key={k} className="flex items-center gap-1.5">
                <span className="inline-block w-4 h-1.5 rounded" style={{ backgroundColor: c }} />
                {k} edge
              </span>
            ))}
          </div>
          
          {taintMode && (
            <div className="flex gap-4 flex-wrap text-sm text-surface-600 font-medium border-l pl-4">
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full border-2 border-green-500"></span> Source</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-red-500"></span> Sink</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-yellow-500"></span> Tainted</span>
              <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-purple-600"></span><span className="w-1.5 h-1.5 bg-purple-600 ml-1"></span> Attack Path</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
