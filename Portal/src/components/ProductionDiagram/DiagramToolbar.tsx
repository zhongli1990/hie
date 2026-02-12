/**
 * Toolbar for Production Diagram
 * Provides zoom, fit view, and view mode controls
 */

import { ZoomIn, ZoomOut, Maximize2, LayoutGrid, Network, GitBranch, Table } from "lucide-react";
import type { ViewMode } from "./types";

interface DiagramToolbarProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFitView: () => void;
  showStatus: boolean;
  showMetrics: boolean;
  showLabels: boolean;
  onToggleStatus: () => void;
  onToggleMetrics: () => void;
  onToggleLabels: () => void;
}

export function DiagramToolbar({
  viewMode,
  onViewModeChange,
  onZoomIn,
  onZoomOut,
  onFitView,
  showStatus,
  showMetrics,
  showLabels,
  onToggleStatus,
  onToggleMetrics,
  onToggleLabels,
}: DiagramToolbarProps) {
  return (
    <div className="bg-white border rounded-lg p-3 shadow-sm mb-4">
      <div className="flex items-center justify-between flex-wrap gap-4">
        {/* Zoom Controls */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700 mr-2">Zoom:</span>
          <button
            onClick={onZoomIn}
            className="p-2 rounded hover:bg-gray-100 border"
            title="Zoom In"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            onClick={onZoomOut}
            className="p-2 rounded hover:bg-gray-100 border"
            title="Zoom Out"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <button
            onClick={onFitView}
            className="p-2 rounded hover:bg-gray-100 border"
            title="Fit View"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>

        {/* View Mode Selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700 mr-2">View:</span>
          <button
            onClick={() => onViewModeChange("column")}
            className={`
              px-3 py-2 rounded text-sm flex items-center gap-2 border
              ${viewMode === "column" ? "bg-nhs-blue text-white" : "bg-white hover:bg-gray-100"}
            `}
            title="Column View"
          >
            <LayoutGrid className="h-4 w-4" />
            Column
          </button>
          <button
            onClick={() => onViewModeChange("graph")}
            className={`
              px-3 py-2 rounded text-sm flex items-center gap-2 border
              ${viewMode === "graph" ? "bg-nhs-blue text-white" : "bg-white hover:bg-gray-100"}
            `}
            title="Graph View"
          >
            <Network className="h-4 w-4" />
            Graph
          </button>
          <button
            onClick={() => onViewModeChange("topology")}
            className={`
              px-3 py-2 rounded text-sm flex items-center gap-2 border
              ${viewMode === "topology" ? "bg-nhs-blue text-white" : "bg-white hover:bg-gray-100"}
            `}
            title="Topology View"
          >
            <GitBranch className="h-4 w-4" />
            Topology
          </button>
          <button
            onClick={() => onViewModeChange("table")}
            className={`
              px-3 py-2 rounded text-sm flex items-center gap-2 border
              ${viewMode === "table" ? "bg-nhs-blue text-white" : "bg-white hover:bg-gray-100"}
            `}
            title="Table View"
          >
            <Table className="h-4 w-4" />
            Table
          </button>
        </div>

        {/* Display Options */}
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-700 mr-2">Show:</span>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showStatus}
              onChange={onToggleStatus}
              className="rounded"
            />
            Status
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showMetrics}
              onChange={onToggleMetrics}
              className="rounded"
            />
            Metrics
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showLabels}
              onChange={onToggleLabels}
              className="rounded"
            />
            Labels
          </label>
        </div>
      </div>
    </div>
  );
}
