/**
 * Enhanced table view for topology items
 * Features: Sorting, filtering, CSV export, row selection
 */

"use client";

import { useState, useMemo } from "react";
import { Search, Download, ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";
import type { ProjectItem, ItemType } from "./types";

interface TopologyTableProps {
  items: ProjectItem[];
  onItemClick: (item: ProjectItem) => void;
}

type SortColumn = "name" | "item_type" | "class_name" | "enabled" | "pool_size";
type SortDirection = "asc" | "desc";

export function TopologyTable({ items, onItemClick }: TopologyTableProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [sortColumn, setSortColumn] = useState<SortColumn>("name");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [typeFilter, setTypeFilter] = useState<ItemType | "all">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "running" | "stopped">("all");

  // Handle column sort
  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  // Filter and sort items
  const filteredAndSortedItems = useMemo(() => {
    let filtered = [...items];

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (item) =>
          item.name.toLowerCase().includes(query) ||
          item.class_name.toLowerCase().includes(query)
      );
    }

    // Apply type filter
    if (typeFilter !== "all") {
      filtered = filtered.filter((item) => item.item_type === typeFilter);
    }

    // Apply status filter
    if (statusFilter !== "all") {
      filtered = filtered.filter((item) =>
        statusFilter === "running" ? item.enabled : !item.enabled
      );
    }

    // Sort
    filtered.sort((a, b) => {
      let aVal: any;
      let bVal: any;

      switch (sortColumn) {
        case "name":
          aVal = a.name.toLowerCase();
          bVal = b.name.toLowerCase();
          break;
        case "item_type":
          aVal = a.item_type;
          bVal = b.item_type;
          break;
        case "class_name":
          aVal = a.class_name;
          bVal = b.class_name;
          break;
        case "enabled":
          aVal = a.enabled ? 1 : 0;
          bVal = b.enabled ? 1 : 0;
          break;
        case "pool_size":
          aVal = a.pool_size;
          bVal = b.pool_size;
          break;
        default:
          aVal = a.name;
          bVal = b.name;
      }

      if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
      if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [items, searchQuery, typeFilter, statusFilter, sortColumn, sortDirection]);

  // Export to CSV
  const handleExportCSV = () => {
    const headers = ["Name", "Type", "Class", "Status", "Pool Size", "Category"];
    const rows = filteredAndSortedItems.map((item) => [
      item.name,
      item.item_type,
      item.class_name,
      item.enabled ? "Running" : "Stopped",
      item.pool_size.toString(),
      item.category || "",
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(",")),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `topology-items-${new Date().toISOString().split("T")[0]}.csv`;
    link.click();
  };

  return (
    <div className="bg-white rounded-lg border shadow-sm overflow-hidden" style={{ height: "calc(100vh - 260px)", minHeight: "500px" }}>
      {/* Toolbar */}
      <div className="px-4 py-3 border-b bg-gray-50 space-y-3">
        {/* Search and Export */}
        <div className="flex items-center gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name or class..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-nhs-blue focus:border-nhs-blue"
            />
          </div>
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-nhs-blue bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
            title="Export to CSV"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4">
          <span className="text-xs font-medium text-gray-600">Filters:</span>

          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as ItemType | "all")}
            className="px-3 py-1.5 text-sm border rounded-lg focus:ring-2 focus:ring-nhs-blue"
          >
            <option value="all">All Types</option>
            <option value="service">Service</option>
            <option value="process">Process</option>
            <option value="operation">Operation</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as "all" | "running" | "stopped")}
            className="px-3 py-1.5 text-sm border rounded-lg focus:ring-2 focus:ring-nhs-blue"
          >
            <option value="all">All Statuses</option>
            <option value="running">Running</option>
            <option value="stopped">Stopped</option>
          </select>

          <span className="text-xs text-gray-500 ml-auto">
            Showing {filteredAndSortedItems.length} of {items.length} items
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-auto" style={{ height: "calc(100% - 120px)" }}>
        <table className="w-full">
          <thead className="bg-gray-50 sticky top-0 z-10">
            <tr className="border-b">
              <SortableHeader
                label="Name"
                column="name"
                currentColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
              />
              <SortableHeader
                label="Type"
                column="item_type"
                currentColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
              />
              <SortableHeader
                label="Class"
                column="class_name"
                currentColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
              />
              <SortableHeader
                label="Status"
                column="enabled"
                currentColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
              />
              <SortableHeader
                label="Pool Size"
                column="pool_size"
                currentColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
              />
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                Category
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredAndSortedItems.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-gray-500">
                  <p className="text-sm">No items match your filters</p>
                  <p className="text-xs text-gray-400 mt-1">Try adjusting your search or filters</p>
                </td>
              </tr>
            ) : (
              filteredAndSortedItems.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => onItemClick(item)}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="py-3 px-4">
                    <span className="font-medium text-gray-900">{item.name}</span>
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getTypeColorClass(
                        item.item_type
                      )}`}
                    >
                      {item.item_type}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-600">
                    <code className="text-xs">{item.class_name}</code>
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-flex items-center gap-2 text-sm ${
                        item.enabled ? "text-green-600" : "text-gray-400"
                      }`}
                    >
                      <span
                        className={`inline-block w-2 h-2 rounded-full ${
                          item.enabled ? "bg-green-500" : "bg-gray-400"
                        }`}
                      />
                      {item.enabled ? "Running" : "Stopped"}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-900">{item.pool_size}</td>
                  <td className="py-3 px-4 text-sm text-gray-600">{item.category || "-"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface SortableHeaderProps {
  label: string;
  column: SortColumn;
  currentColumn: SortColumn;
  direction: SortDirection;
  onSort: (column: SortColumn) => void;
}

function SortableHeader({
  label,
  column,
  currentColumn,
  direction,
  onSort,
}: SortableHeaderProps) {
  const isActive = currentColumn === column;

  return (
    <th
      onClick={() => onSort(column)}
      className="text-left py-3 px-4 text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-100 transition-colors select-none"
    >
      <div className="flex items-center gap-2">
        {label}
        {isActive ? (
          direction === "asc" ? (
            <ChevronUp className="h-4 w-4 text-nhs-blue" />
          ) : (
            <ChevronDown className="h-4 w-4 text-nhs-blue" />
          )
        ) : (
          <ChevronsUpDown className="h-4 w-4 text-gray-400" />
        )}
      </div>
    </th>
  );
}

function getTypeColorClass(type: ItemType): string {
  switch (type) {
    case "service":
      return "bg-green-100 text-green-700";
    case "process":
      return "bg-blue-100 text-blue-700";
    case "operation":
      return "bg-purple-100 text-purple-700";
    default:
      return "bg-gray-100 text-gray-700";
  }
}
