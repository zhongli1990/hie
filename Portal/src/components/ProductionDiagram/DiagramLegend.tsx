/**
 * Legend component for Production Topology
 * Shows color coding and connection types
 */

export function DiagramLegend() {
  return (
    <div className="bg-white border rounded-lg p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-6">
        {/* Item Types */}
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700">Item Types:</span>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-green-50 border-2 border-green-600 rounded" />
            <span className="text-xs text-gray-600">Service (Inbound)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-blue-50 border-2 border-nhs-blue rounded" />
            <span className="text-xs text-gray-600">Process (Transform)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-purple-50 border-2 border-purple-600 rounded" />
            <span className="text-xs text-gray-600">Operation (Outbound)</span>
          </div>
        </div>

        {/* Connection Types */}
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700">Connections:</span>
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 bg-nhs-blue" />
            <span className="text-xs text-gray-600">Standard</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 bg-yellow-500" style={{ backgroundImage: "repeating-linear-gradient(to right, #ffb81c 0, #ffb81c 2px, transparent 2px, transparent 5px)" }} />
            <span className="text-xs text-gray-600">Async</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 bg-red-500" style={{ backgroundImage: "repeating-linear-gradient(to right, #da291c 0, #da291c 6px, transparent 6px, transparent 10px)" }} />
            <span className="text-xs text-gray-600">Error</span>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700">Status:</span>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full" />
            <span className="text-xs text-gray-600">Running</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-gray-400 rounded-full" />
            <span className="text-xs text-gray-600">Stopped</span>
          </div>
        </div>
      </div>
    </div>
  );
}
