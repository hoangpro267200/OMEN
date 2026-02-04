/**
 * LineageGraph - Data lineage visualization for signal processing
 * 
 * Shows how data flows through OMEN pipeline:
 * Source → Ingest → Validate → Enrich → Classify → Signal → Ledger
 * 
 * Features:
 * - Custom styled nodes with status indicators
 * - Animated edges showing data flow
 * - Click to see node details
 * - Minimap and controls
 */

import React, { useMemo, useCallback, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  NodeTypes,
  Handle,
  Position,
  BackgroundVariant,
  type NodeProps,
  type EdgeProps,
  getBezierPath,
} from 'reactflow';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Database,
  GitBranch,
  Shield,
  Radio,
  CheckCircle,
  XCircle,
  Clock,
  Zap,
  AlertTriangle,
  FileText,
  X,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import 'reactflow/dist/style.css';

// ============================================================================
// TYPES
// ============================================================================

export interface LineageNodeData {
  type: 'source' | 'process' | 'output' | 'rejected';
  label: string;
  status: 'passed' | 'failed' | 'processing' | 'idle';
  duration_ms?: number;
  input_count?: number;
  output_count?: number;
  rule_name?: string;
  rule_version?: string;
  error?: string;
  details?: Record<string, unknown>;
}

interface LineageEdgeData {
  label?: string;
  count?: number;
  latency_ms?: number;
  animated?: boolean;
}

// ============================================================================
// CUSTOM NODE COMPONENT
// ============================================================================

function LineageNodeComponent({ data, selected }: NodeProps<LineageNodeData>) {
  const statusConfig = {
    passed: {
      border: 'border-[var(--status-success)]',
      bg: 'bg-[var(--status-success)]/10',
      icon: <CheckCircle className="w-4 h-4 text-[var(--status-success)]" />,
    },
    failed: {
      border: 'border-[var(--status-error)]',
      bg: 'bg-[var(--status-error)]/10',
      icon: <XCircle className="w-4 h-4 text-[var(--status-error)]" />,
    },
    processing: {
      border: 'border-[var(--accent-amber)]',
      bg: 'bg-[var(--accent-amber)]/10',
      icon: <Clock className="w-4 h-4 text-[var(--accent-amber)] animate-spin" />,
    },
    idle: {
      border: 'border-[var(--border-subtle)]',
      bg: 'bg-[var(--bg-tertiary)]',
      icon: null,
    },
  };

  const typeConfig = {
    source: { icon: <Database className="w-5 h-5" />, color: 'text-[var(--accent-cyan)]' },
    process: { icon: <GitBranch className="w-5 h-5" />, color: 'text-[var(--accent-amber)]' },
    output: { icon: <Radio className="w-5 h-5" />, color: 'text-[var(--status-success)]' },
    rejected: { icon: <AlertTriangle className="w-5 h-5" />, color: 'text-[var(--status-error)]' },
  };

  const status = statusConfig[data.status];
  const type = typeConfig[data.type];

  return (
    <div
      className={cn(
        'relative px-4 py-3 rounded-xl border-2 min-w-[160px]',
        'backdrop-blur-sm transition-all duration-200',
        status.border,
        status.bg,
        selected && 'ring-2 ring-[var(--accent-cyan)] ring-offset-2 ring-offset-[var(--bg-primary)] scale-105'
      )}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-[var(--bg-tertiary)] !border-2 !border-[var(--border-default)]"
      />

      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <span className={type.color}>{type.icon}</span>
        <span className="text-sm font-semibold text-[var(--text-primary)]">{data.label}</span>
        {status.icon}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        {data.duration_ms !== undefined && (
          <>
            <span className="text-[var(--text-muted)]">Time</span>
            <span className="font-mono text-[var(--text-secondary)] text-right">{data.duration_ms}ms</span>
          </>
        )}
        {data.input_count !== undefined && (
          <>
            <span className="text-[var(--text-muted)]">In</span>
            <span className="font-mono text-[var(--text-secondary)] text-right">
              {data.input_count.toLocaleString()}
            </span>
          </>
        )}
        {data.output_count !== undefined && (
          <>
            <span className="text-[var(--text-muted)]">Out</span>
            <span className="font-mono text-[var(--status-success)] text-right">
              {data.output_count.toLocaleString()}
            </span>
          </>
        )}
      </div>

      {/* Rule Badge */}
      {data.rule_name && (
        <div className="mt-2 pt-2 border-t border-[var(--border-subtle)]">
          <div className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
            <Shield className="w-3 h-3" />
            <span className="truncate">{data.rule_name}</span>
            {data.rule_version && (
              <span className="px-1 bg-[var(--bg-tertiary)] rounded">v{data.rule_version}</span>
            )}
          </div>
        </div>
      )}

      {/* Error Banner */}
      {data.error && (
        <div className="mt-2 p-2 rounded bg-[var(--status-error)]/20 text-[10px] text-[var(--status-error)] flex items-start gap-1">
          <AlertTriangle className="w-3 h-3 flex-shrink-0 mt-0.5" />
          <span>{data.error}</span>
        </div>
      )}

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-[var(--bg-tertiary)] !border-2 !border-[var(--border-default)]"
      />
    </div>
  );
}

// ============================================================================
// CUSTOM EDGE COMPONENT
// ============================================================================

function LineageEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style,
  markerEnd,
}: EdgeProps<LineageEdgeData>) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const isAnimated = data?.animated;
  const strokeColor = style?.stroke || (isAnimated ? '#00f0ff' : '#4b5563');

  return (
    <>
      {/* Glow Filter Definition */}
      <defs>
        <filter id={`glow-${id}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Base Edge */}
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        style={{
          strokeWidth: 2,
          stroke: strokeColor,
          strokeDasharray: isAnimated ? '5,5' : 'none',
          fill: 'none',
        }}
        markerEnd={markerEnd}
      />

      {/* Animated Particle */}
      {isAnimated && (
        <circle r={4} fill="#00f0ff" filter={`url(#glow-${id})`}>
          <animateMotion dur="2s" repeatCount="indefinite" path={edgePath} />
        </circle>
      )}

      {/* Edge Label */}
      {data?.count !== undefined && (
        <foreignObject x={labelX - 25} y={labelY - 10} width={50} height={20} className="pointer-events-none">
          <div className="flex items-center justify-center h-full">
            <span className="px-2 py-0.5 rounded bg-[var(--bg-secondary)]/90 text-[10px] text-[var(--accent-cyan)] font-mono border border-[var(--border-subtle)]">
              {data.count.toLocaleString()}
            </span>
          </div>
        </foreignObject>
      )}
    </>
  );
}

// ============================================================================
// NODE/EDGE TYPE REGISTRATION
// ============================================================================

const nodeTypes: NodeTypes = {
  lineageNode: LineageNodeComponent,
};

const edgeTypes = {
  lineageEdge: LineageEdgeComponent,
};

// ============================================================================
// GENERATE LINEAGE DATA FROM SIGNAL
// ============================================================================

interface SignalLineageData {
  signal_id: string;
  explanation_chain?: {
    steps?: Array<{
      step_id: number;
      rule_name: string;
      rule_version?: string;
      duration_ms?: number;
      input_summary?: Record<string, unknown>;
      output_summary?: Record<string, unknown>;
    }>;
  };
}

function generateLineageFromSignal(
  signalId: string,
  signalData?: SignalLineageData
): { nodes: Node<LineageNodeData>[]; edges: Edge<LineageEdgeData>[] } {
  // Default pipeline visualization
  const nodes: Node<LineageNodeData>[] = [
    // Source
    {
      id: 'source',
      type: 'lineageNode',
      position: { x: 0, y: 100 },
      data: {
        type: 'source',
        label: 'Polymarket',
        status: 'passed',
        output_count: 1250,
      },
    },
    // Ingest
    {
      id: 'ingest',
      type: 'lineageNode',
      position: { x: 220, y: 100 },
      data: {
        type: 'process',
        label: 'Ingest',
        status: 'passed',
        duration_ms: 10,
        input_count: 1250,
        output_count: 1250,
        rule_name: 'event_mapper',
        rule_version: '1.2.0',
      },
    },
    // Validate
    {
      id: 'validate',
      type: 'lineageNode',
      position: { x: 440, y: 50 },
      data: {
        type: 'process',
        label: 'Validate',
        status: 'passed',
        duration_ms: 75,
        input_count: 1250,
        output_count: 520,
        rule_name: 'validation_pipeline',
        rule_version: '2.1.0',
      },
    },
    // Rejected
    {
      id: 'rejected',
      type: 'lineageNode',
      position: { x: 440, y: 200 },
      data: {
        type: 'rejected',
        label: 'Rejected',
        status: 'failed',
        input_count: 730,
        error: 'Low liquidity, irrelevant content',
      },
    },
    // Enrich
    {
      id: 'enrich',
      type: 'lineageNode',
      position: { x: 660, y: 50 },
      data: {
        type: 'process',
        label: 'Enrich',
        status: 'passed',
        duration_ms: 55,
        input_count: 520,
        output_count: 520,
        rule_name: 'enrichment_pipeline',
        rule_version: '1.5.0',
      },
    },
    // Classify
    {
      id: 'classify',
      type: 'lineageNode',
      position: { x: 880, y: 50 },
      data: {
        type: 'process',
        label: 'Classify',
        status: 'passed',
        duration_ms: 25,
        input_count: 520,
        output_count: 520,
        rule_name: 'signal_classifier',
        rule_version: '1.3.0',
      },
    },
    // Signal Output
    {
      id: 'signal',
      type: 'lineageNode',
      position: { x: 1100, y: 0 },
      data: {
        type: 'output',
        label: 'Signal',
        status: 'passed',
        input_count: 520,
        output_count: 47,
      },
    },
    // Ledger
    {
      id: 'ledger',
      type: 'lineageNode',
      position: { x: 1100, y: 100 },
      data: {
        type: 'output',
        label: 'Ledger',
        status: 'passed',
        input_count: 47,
        output_count: 47,
        rule_name: 'wal_writer',
        rule_version: '1.0.0',
      },
    },
  ];

  const edges: Edge<LineageEdgeData>[] = [
    {
      id: 'source-ingest',
      source: 'source',
      target: 'ingest',
      type: 'lineageEdge',
      data: { count: 1250, animated: true },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#4b5563' },
    },
    {
      id: 'ingest-validate',
      source: 'ingest',
      target: 'validate',
      type: 'lineageEdge',
      data: { count: 1250, animated: true },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#4b5563' },
    },
    {
      id: 'ingest-rejected',
      source: 'ingest',
      target: 'rejected',
      type: 'lineageEdge',
      data: { count: 730 },
      style: { stroke: '#ef4444' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#ef4444' },
    },
    {
      id: 'validate-enrich',
      source: 'validate',
      target: 'enrich',
      type: 'lineageEdge',
      data: { count: 520, animated: true },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#4b5563' },
    },
    {
      id: 'enrich-classify',
      source: 'enrich',
      target: 'classify',
      type: 'lineageEdge',
      data: { count: 520, animated: true },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#4b5563' },
    },
    {
      id: 'classify-signal',
      source: 'classify',
      target: 'signal',
      type: 'lineageEdge',
      data: { count: 47, animated: true },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981' },
    },
    {
      id: 'signal-ledger',
      source: 'signal',
      target: 'ledger',
      type: 'lineageEdge',
      data: { count: 47, animated: true },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981' },
    },
  ];

  return { nodes, edges };
}

// ============================================================================
// MAIN LINEAGE GRAPH COMPONENT
// ============================================================================

interface LineageGraphProps {
  signalId: string;
  signalData?: SignalLineageData;
  onNodeClick?: (nodeId: string, data: LineageNodeData) => void;
  className?: string;
}

export function LineageGraph({ signalId, signalData, onNodeClick, className }: LineageGraphProps) {
  // Generate nodes and edges
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => generateLineageFromSignal(signalId, signalData),
    [signalId, signalData]
  );

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  // Handle node click
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node<LineageNodeData>) => {
      onNodeClick?.(node.id, node.data);
    },
    [onNodeClick]
  );

  return (
    <div className={cn('w-full h-[400px] rounded-xl overflow-hidden bg-[var(--bg-primary)]/50', className)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={1.5}
        defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#374151" />
        <Controls className="!bg-[var(--bg-secondary)] !border-[var(--border-subtle)] !rounded-lg" showInteractive={false} />
        <MiniMap
          className="!bg-[var(--bg-secondary)] !border-[var(--border-subtle)] !rounded-lg"
          nodeColor={(node) => {
            const data = node.data as LineageNodeData;
            if (data.status === 'passed') return '#10b981';
            if (data.status === 'failed') return '#ef4444';
            if (data.status === 'processing') return '#f59e0b';
            return '#6b7280';
          }}
          maskColor="rgba(0, 0, 0, 0.8)"
        />
      </ReactFlow>
    </div>
  );
}

// ============================================================================
// LINEAGE DETAIL PANEL (Shows when node is clicked)
// ============================================================================

interface LineageDetailPanelProps {
  nodeId: string | null;
  nodeData: LineageNodeData | null;
  onClose: () => void;
}

export function LineageDetailPanel({ nodeId, nodeData, onClose }: LineageDetailPanelProps) {
  if (!nodeId || !nodeData) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 20 }}
        className={cn(
          'absolute right-4 top-4 w-80 rounded-xl overflow-hidden',
          'bg-[var(--bg-secondary)]/95 backdrop-blur-xl border border-[var(--border-subtle)]',
          'shadow-2xl'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--bg-tertiary)]/50">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-[var(--accent-cyan)]" />
            <span className="font-medium text-[var(--text-primary)]">{nodeData.label}</span>
          </div>
          <button onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Status */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-[var(--text-muted)]">Status</span>
            <span
              className={cn(
                'px-2 py-0.5 rounded text-xs font-medium',
                nodeData.status === 'passed' && 'bg-[var(--status-success)]/20 text-[var(--status-success)]',
                nodeData.status === 'failed' && 'bg-[var(--status-error)]/20 text-[var(--status-error)]',
                nodeData.status === 'processing' && 'bg-[var(--accent-amber)]/20 text-[var(--accent-amber)]'
              )}
            >
              {nodeData.status.toUpperCase()}
            </span>
          </div>

          {/* Metrics */}
          <div className="space-y-2">
            {nodeData.duration_ms !== undefined && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-[var(--text-muted)]">Processing Time</span>
                <span className="font-mono text-[var(--text-primary)]">{nodeData.duration_ms}ms</span>
              </div>
            )}
            {nodeData.input_count !== undefined && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-[var(--text-muted)]">Input Events</span>
                <span className="font-mono text-[var(--text-primary)]">{nodeData.input_count.toLocaleString()}</span>
              </div>
            )}
            {nodeData.output_count !== undefined && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-[var(--text-muted)]">Output Events</span>
                <span className="font-mono text-[var(--status-success)]">{nodeData.output_count.toLocaleString()}</span>
              </div>
            )}
          </div>

          {/* Rule Info */}
          {nodeData.rule_name && (
            <div className="pt-3 border-t border-[var(--border-subtle)]">
              <div className="text-xs text-[var(--text-muted)] mb-2">Rule Applied</div>
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-[var(--accent-amber)]" />
                <span className="text-sm text-[var(--text-primary)]">{nodeData.rule_name}</span>
                {nodeData.rule_version && (
                  <span className="px-1.5 py-0.5 bg-[var(--bg-tertiary)] rounded text-[10px] text-[var(--text-muted)]">
                    v{nodeData.rule_version}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Error */}
          {nodeData.error && (
            <div className="p-3 rounded-lg bg-[var(--status-error)]/10 border border-[var(--status-error)]/20">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-[var(--status-error)] flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-medium text-[var(--status-error)] mb-1">Error Details</div>
                  <div className="text-xs text-[var(--status-error)]/80">{nodeData.error}</div>
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="pt-3 border-t border-[var(--border-subtle)] flex gap-2">
            <button className="flex-1 px-3 py-2 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--bg-elevated)] text-xs text-[var(--text-secondary)] transition-colors">
              View Logs
            </button>
            <button className="flex-1 px-3 py-2 rounded-lg bg-[var(--accent-cyan)]/20 hover:bg-[var(--accent-cyan)]/30 text-xs text-[var(--accent-cyan)] transition-colors">
              View Rule
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export default LineageGraph;
