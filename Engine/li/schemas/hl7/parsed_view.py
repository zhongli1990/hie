"""
LI HL7 Parsed View

Provides lazy parsed view for HL7v2 messages.
Fields are parsed on-demand and cached.
"""

from __future__ import annotations

import re
from typing import Any, TYPE_CHECKING

from Engine.li.schemas.base import ParsedView

if TYPE_CHECKING:
    from Engine.li.schemas.hl7.schema import HL7Schema


class HL7ParsedView(ParsedView):
    """
    Lazy parsed view for HL7v2 messages.
    
    Supports field access using HL7 path notation:
    - "MSH-9" - Field 9 of MSH segment
    - "MSH-9.1" - Component 1 of field 9
    - "MSH-9.1.2" - Subcomponent 2 of component 1
    - "PID-3(1)" - First repetition of field 3
    - "PID-3(1).1" - Component 1 of first repetition
    
    Also supports segment access:
    - "MSH" - Entire MSH segment as string
    - "PID" - First PID segment
    - "OBX(2)" - Second OBX segment
    """
    
    # HL7 delimiters (defaults, can be overridden from MSH)
    FIELD_SEP = "|"
    COMPONENT_SEP = "^"
    REPETITION_SEP = "~"
    ESCAPE_CHAR = "\\"
    SUBCOMPONENT_SEP = "&"
    
    def __init__(self, raw: bytes, schema: "HL7Schema"):
        super().__init__(raw, schema)
        
        # Parsed structure (lazy)
        self._segments: list[str] | None = None
        self._segment_map: dict[str, list[str]] | None = None
        self._delimiters_parsed = False
    
    def _ensure_parsed(self) -> None:
        """Ensure message structure is parsed."""
        if self._segments is not None:
            return
        
        # Decode raw bytes
        text = self._raw.decode("utf-8", errors="replace")
        
        # Normalize line endings
        text = text.replace("\r\n", "\r").replace("\n", "\r")
        
        # Split into segments
        self._segments = [s for s in text.split("\r") if s.strip()]
        
        # Parse delimiters from MSH
        if self._segments and self._segments[0].startswith("MSH"):
            self._parse_delimiters(self._segments[0])
        
        # Build segment map
        self._segment_map = {}
        for seg in self._segments:
            if len(seg) >= 3:
                seg_name = seg[:3]
                if seg_name not in self._segment_map:
                    self._segment_map[seg_name] = []
                self._segment_map[seg_name].append(seg)
        
        self._parsed = True
    
    def _parse_delimiters(self, msh: str) -> None:
        """Parse delimiters from MSH segment."""
        if len(msh) >= 8:
            self.FIELD_SEP = msh[3]
            self.COMPONENT_SEP = msh[4]
            self.REPETITION_SEP = msh[5]
            self.ESCAPE_CHAR = msh[6]
            self.SUBCOMPONENT_SEP = msh[7]
        self._delimiters_parsed = True
    
    def get_field(self, path: str, default: Any = None) -> Any:
        """
        Get a field value by HL7 path.
        
        Path formats:
        - "MSH-9" - Field 9 of MSH
        - "MSH-9.1" - Component 1 of field 9
        - "MSH-9.1.2" - Subcomponent 2 of component 1
        - "PID-3(1)" - First repetition of field 3
        - "PID-3(1).1" - Component 1 of first repetition
        - "MSH" - Entire MSH segment
        - "OBX(2)" - Second OBX segment
        
        Args:
            path: HL7 field path
            default: Default value if not found
            
        Returns:
            Field value or default
        """
        # Check cache
        if path in self._cache:
            return self._cache[path]
        
        self._ensure_parsed()
        
        try:
            value = self._get_field_internal(path)
            self._cache[path] = value
            return value if value is not None else default
        except (IndexError, KeyError, ValueError):
            return default
    
    def _get_field_internal(self, path: str) -> Any:
        """Internal field access implementation."""
        # Parse path: SEG-FIELD(REP).COMP.SUBCOMP
        # Examples: MSH-9, MSH-9.1, PID-3(1).1, OBX(2)-5
        
        # Check for segment-only access (e.g., "MSH", "OBX(2)")
        seg_only_match = re.match(r'^([A-Z]{2,3})(?:\((\d+)\))?$', path)
        if seg_only_match:
            seg_name = seg_only_match.group(1)
            seg_rep = int(seg_only_match.group(2) or 1) - 1
            segments = self._segment_map.get(seg_name, [])
            if seg_rep < len(segments):
                return segments[seg_rep]
            return None
        
        # Parse full path
        match = re.match(
            r'^([A-Z]{2,3})(?:\((\d+)\))?-(\d+)(?:\((\d+)\))?(?:\.(\d+)(?:\.(\d+))?)?$',
            path
        )
        
        if not match:
            raise ValueError(f"Invalid HL7 path: {path}")
        
        seg_name = match.group(1)
        seg_rep = int(match.group(2) or 1) - 1
        field_num = int(match.group(3))
        field_rep = int(match.group(4) or 1) - 1
        comp_num = int(match.group(5)) if match.group(5) else None
        subcomp_num = int(match.group(6)) if match.group(6) else None
        
        # Get segment
        segments = self._segment_map.get(seg_name, [])
        if seg_rep >= len(segments):
            return None
        segment = segments[seg_rep]
        
        # Special handling for MSH - field 1 is the separator itself
        if seg_name == "MSH":
            if field_num == 1:
                return self.FIELD_SEP
            if field_num == 2:
                return segment[4:8] if len(segment) >= 8 else None
            # For MSH, field numbers are offset by 1 due to separator
            field_num -= 1
        
        # Split segment into fields
        fields = segment.split(self.FIELD_SEP)
        
        # Get field (1-indexed, but fields[0] is segment name)
        if field_num >= len(fields):
            return None
        field_value = fields[field_num]
        
        # Handle repetitions
        if self.REPETITION_SEP in field_value:
            repetitions = field_value.split(self.REPETITION_SEP)
            if field_rep >= len(repetitions):
                return None
            field_value = repetitions[field_rep]
        elif field_rep > 0:
            return None
        
        # Handle components
        if comp_num is not None:
            components = field_value.split(self.COMPONENT_SEP)
            if comp_num > len(components):
                return None
            comp_value = components[comp_num - 1]
            
            # Handle subcomponents
            if subcomp_num is not None:
                subcomponents = comp_value.split(self.SUBCOMPONENT_SEP)
                if subcomp_num > len(subcomponents):
                    return None
                return subcomponents[subcomp_num - 1] or None
            
            return comp_value or None
        
        return field_value or None
    
    def set_field(self, path: str, value: Any) -> bytes:
        """
        Set a field value and return new raw bytes.
        
        Does NOT modify the original raw bytes.
        
        Args:
            path: HL7 field path
            value: New field value
            
        Returns:
            New raw bytes with field updated
        """
        self._ensure_parsed()
        
        # Parse path
        match = re.match(
            r'^([A-Z]{2,3})(?:\((\d+)\))?-(\d+)(?:\((\d+)\))?(?:\.(\d+)(?:\.(\d+))?)?$',
            path
        )
        
        if not match:
            raise ValueError(f"Invalid HL7 path: {path}")
        
        seg_name = match.group(1)
        seg_rep = int(match.group(2) or 1) - 1
        field_num = int(match.group(3))
        field_rep = int(match.group(4) or 1) - 1
        comp_num = int(match.group(5)) if match.group(5) else None
        subcomp_num = int(match.group(6)) if match.group(6) else None
        
        # Find segment index in full list
        seg_count = 0
        seg_idx = None
        for i, seg in enumerate(self._segments):
            if seg[:3] == seg_name:
                if seg_count == seg_rep:
                    seg_idx = i
                    break
                seg_count += 1
        
        if seg_idx is None:
            raise ValueError(f"Segment not found: {seg_name}({seg_rep + 1})")
        
        # Get and modify segment
        segment = self._segments[seg_idx]
        fields = segment.split(self.FIELD_SEP)
        
        # Adjust field number for MSH
        actual_field_num = field_num
        if seg_name == "MSH" and field_num > 1:
            actual_field_num = field_num - 1
        
        # Extend fields if needed
        while len(fields) <= actual_field_num:
            fields.append("")
        
        # Get current field value
        field_value = fields[actual_field_num]
        
        # Handle repetitions
        repetitions = field_value.split(self.REPETITION_SEP) if self.REPETITION_SEP in field_value else [field_value]
        while len(repetitions) <= field_rep:
            repetitions.append("")
        
        if comp_num is not None:
            # Handle components
            components = repetitions[field_rep].split(self.COMPONENT_SEP)
            while len(components) < comp_num:
                components.append("")
            
            if subcomp_num is not None:
                # Handle subcomponents
                subcomponents = components[comp_num - 1].split(self.SUBCOMPONENT_SEP)
                while len(subcomponents) < subcomp_num:
                    subcomponents.append("")
                subcomponents[subcomp_num - 1] = str(value)
                components[comp_num - 1] = self.SUBCOMPONENT_SEP.join(subcomponents)
            else:
                components[comp_num - 1] = str(value)
            
            repetitions[field_rep] = self.COMPONENT_SEP.join(components)
        else:
            repetitions[field_rep] = str(value)
        
        fields[actual_field_num] = self.REPETITION_SEP.join(repetitions)
        
        # Rebuild segment
        new_segment = self.FIELD_SEP.join(fields)
        
        # Rebuild message
        new_segments = self._segments.copy()
        new_segments[seg_idx] = new_segment
        
        return "\r".join(new_segments).encode("utf-8")
    
    def get_segment(self, name: str, index: int = 0) -> str | None:
        """
        Get a segment by name.
        
        Args:
            name: Segment name (e.g., "MSH", "PID")
            index: Segment index for repeating segments (0-indexed)
            
        Returns:
            Segment string or None
        """
        self._ensure_parsed()
        segments = self._segment_map.get(name, [])
        if index < len(segments):
            return segments[index]
        return None
    
    def get_segments(self, name: str) -> list[str]:
        """
        Get all segments with a given name.
        
        Args:
            name: Segment name
            
        Returns:
            List of segment strings
        """
        self._ensure_parsed()
        return self._segment_map.get(name, [])
    
    def get_message_type(self) -> str | None:
        """Get message type (MSH-9.1^MSH-9.2)."""
        msg_type = self.get_field("MSH-9.1")
        trigger = self.get_field("MSH-9.2")
        if msg_type and trigger:
            return f"{msg_type}_{trigger}"
        return msg_type
    
    def get_message_control_id(self) -> str | None:
        """Get message control ID (MSH-10)."""
        return self.get_field("MSH-10")
    
    def get_sending_application(self) -> str | None:
        """Get sending application (MSH-3)."""
        return self.get_field("MSH-3")
    
    def get_sending_facility(self) -> str | None:
        """Get sending facility (MSH-4)."""
        return self.get_field("MSH-4")
    
    def get_receiving_application(self) -> str | None:
        """Get receiving application (MSH-5)."""
        return self.get_field("MSH-5")
    
    def get_receiving_facility(self) -> str | None:
        """Get receiving facility (MSH-6)."""
        return self.get_field("MSH-6")
    
    def get_patient_id(self) -> str | None:
        """Get patient ID (PID-3.1)."""
        return self.get_field("PID-3.1")
    
    def get_patient_name(self) -> str | None:
        """Get patient name (PID-5)."""
        return self.get_field("PID-5")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        self._ensure_parsed()
        
        result = {
            "message_type": self.get_message_type(),
            "message_control_id": self.get_message_control_id(),
            "sending_application": self.get_sending_application(),
            "sending_facility": self.get_sending_facility(),
            "segments": {},
        }
        
        for seg_name, segments in self._segment_map.items():
            if len(segments) == 1:
                result["segments"][seg_name] = segments[0]
            else:
                result["segments"][seg_name] = segments
        
        return result
