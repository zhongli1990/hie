/**
 * Icon components for different item types
 */

import { ArrowDownToLine, GitBranch, ArrowUpFromLine } from "lucide-react";
import type { ItemType } from "./types";

interface NodeTypeIconProps {
  type: ItemType;
  className?: string;
}

export function NodeTypeIcon({ type, className = "h-5 w-5" }: NodeTypeIconProps) {
  switch (type) {
    case "service":
      return (
        <span title="Inbound Service">
          <ArrowDownToLine className={className} />
        </span>
      );
    case "process":
      return (
        <span title="Business Process">
          <GitBranch className={className} />
        </span>
      );
    case "operation":
      return (
        <span title="Outbound Operation">
          <ArrowUpFromLine className={className} />
        </span>
      );
    default:
      return null;
  }
}
