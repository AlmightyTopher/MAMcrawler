import xml.etree.ElementTree as ET
from lxml import etree
import re
from typing import List, Dict, Any, Optional, Tuple


class XMLParseError(Exception):
    """Custom exception for XML parsing errors with detailed information."""
    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None,
                 suggestion: Optional[str] = None):
        self.message = message
        self.line = line
        self.column = column
        self.suggestion = suggestion
        super().__init__(self.format_message())

    def format_message(self) -> str:
        msg = self.message
        if self.line is not None:
            msg += f" at line {self.line}"
        if self.column is not None:
            msg += f", column {self.column}"
        if self.suggestion:
            msg += f". Suggestion: {self.suggestion}"
        return msg


class ApplyDiffXMLParser:
    """Robust XML parser for apply_diff operations with comprehensive error handling."""

    def __init__(self):
        self.errors: List[XMLParseError] = []
        self.warnings: List[str] = []

    def parse_xml_string(self, xml_string: str) -> Optional[ET.Element]:
        """
        Parse XML string with error handling and recovery.

        Args:
            xml_string: The XML string to parse

        Returns:
            Root element if parsing successful, None if critical errors
        """
        self.errors.clear()
        self.warnings.clear()

        try:
            # First attempt with standard ElementTree
            root = ET.fromstring(xml_string)
            return root
        except ET.ParseError as e:
            # Try to recover with lxml for better error reporting
            try:
                parser = etree.XMLParser(recover=True)
                tree = etree.fromstring(xml_string.encode('utf-8'), parser=parser)
                if parser.error_log:
                    self._process_lxml_errors(parser.error_log, xml_string)
                return tree
            except etree.XMLSyntaxError as lxml_error:
                self._handle_parse_error(str(e), xml_string)
                return None

    def _process_lxml_errors(self, error_log, xml_string: str):
        """Process lxml error log and convert to our custom errors."""
        lines = xml_string.split('\n')
        for error in error_log:
            line_num = error.line if hasattr(error, 'line') else None
            column_num = error.column if hasattr(error, 'column') else None

            # Extract error message
            message = str(error.message) if hasattr(error, 'message') else str(error)

            # Generate suggestion based on error type
            suggestion = self._generate_suggestion(message, lines, line_num)

            self.errors.append(XMLParseError(message, line_num, column_num, suggestion))

    def _handle_parse_error(self, error_msg: str, xml_string: str):
        """Handle standard ElementTree parse errors."""
        lines = xml_string.split('\n')

        # Try to extract line and column from error message
        line_match = re.search(r'line (\d+)', error_msg)
        column_match = re.search(r'column (\d+)', error_msg)

        line_num = int(line_match.group(1)) if line_match else None
        column_num = int(column_match.group(1)) if column_match else None

        # Check for specific error patterns
        if "unclosed tag" in error_msg.lower():
            tag_match = re.search(r'unclosed tag: ([^,\s]+)', error_msg)
            if tag_match:
                tag = tag_match.group(1)
                suggestion = f"Add closing tag </{tag}>"
            else:
                suggestion = "Ensure all tags are properly closed"
        elif "mismatched tag" in error_msg.lower():
            suggestion = "Check that opening and closing tags match"
        elif "not well-formed" in error_msg.lower():
            suggestion = "Check XML syntax and structure"
        else:
            suggestion = "Validate XML structure"

        self.errors.append(XMLParseError(error_msg, line_num, column_num, suggestion))

    def _generate_suggestion(self, message: str, lines: List[str], line_num: Optional[int]) -> str:
        """Generate helpful suggestions based on error message."""
        message_lower = message.lower()

        if "unclosed" in message_lower and "tag" in message_lower:
            # Try to find the unclosed tag
            if line_num and line_num <= len(lines):
                line = lines[line_num - 1]
                # Look for opening tags without closing
                opening_tags = re.findall(r'<(\w+)[^>]*>', line)
                if opening_tags:
                    return f"Add closing tag </{opening_tags[-1]}>"
            return "Add missing closing tag"

        elif "mismatched" in message_lower:
            return "Ensure opening and closing tags match exactly"

        elif "attribute" in message_lower:
            return "Check attribute syntax: name=\"value\""

        elif "entity" in message_lower:
            return "Use & for &, < for <, > for >"

        else:
            return "Check XML syntax and ensure proper nesting"

    def validate_apply_diff_structure(self, root: ET.Element) -> bool:
        """
        Validate the structure of apply_diff XML.

        Expected structure:
        <apply_diff>
            <args>
                <file>
                    <path>...</path>
                    <diff>
                        <content>...</content>
                        <start_line>...</start_line>
                    </diff>
                    ... more diff elements
                </file>
                ... more file elements
            </args>
        </apply_diff>
        """
        if root.tag != 'apply_diff':
            self.errors.append(XMLParseError(
                f"Root element must be 'apply_diff', found '{root.tag}'",
                suggestion="Wrap content in <apply_diff> tags"
            ))
            return False

        args_elem = root.find('args')
        if args_elem is None:
            self.errors.append(XMLParseError(
                "Missing required 'args' element",
                suggestion="Add <args> element inside <apply_diff>"
            ))
            return False

        file_elems = args_elem.findall('file')
        if not file_elems:
            self.warnings.append("No file elements found in args")
            return True  # Not critical, but warn

        for i, file_elem in enumerate(file_elems):
            if not self._validate_file_element(file_elem, i + 1):
                return False

        return True

    def _validate_file_element(self, file_elem: ET.Element, index: int) -> bool:
        """Validate a single file element."""
        path_elem = file_elem.find('path')
        if path_elem is None:
            self.errors.append(XMLParseError(
                f"File element {index} missing required 'path' element",
                suggestion="Add <path> element inside each <file>"
            ))
            return False

        if not path_elem.text or not path_elem.text.strip():
            self.errors.append(XMLParseError(
                f"File element {index} has empty path",
                suggestion="Provide a valid file path"
            ))
            return False

        diff_elems = file_elem.findall('diff')
        if not diff_elems:
            self.warnings.append(f"File element {index} has no diff elements")
            return True

        for j, diff_elem in enumerate(diff_elems):
            if not self._validate_diff_element(diff_elem, index, j + 1):
                return False

        return True

    def _validate_diff_element(self, diff_elem: ET.Element, file_index: int, diff_index: int) -> bool:
        """Validate a single diff element."""
        content_elem = diff_elem.find('content')
        if content_elem is None:
            self.errors.append(XMLParseError(
                f"Diff element {diff_index} in file {file_index} missing required 'content' element",
                suggestion="Add <content> element inside each <diff>"
            ))
            return False

        start_line_elem = diff_elem.find('start_line')
        if start_line_elem is None:
            self.errors.append(XMLParseError(
                f"Diff element {diff_index} in file {file_index} missing required 'start_line' element",
                suggestion="Add <start_line> element inside each <diff>"
            ))
            return False

        try:
            line_num = int(start_line_elem.text.strip())
            if line_num < 1:
                self.errors.append(XMLParseError(
                    f"Invalid start_line value '{start_line_elem.text}' in diff {diff_index}, file {file_index}",
                    suggestion="Line numbers must be positive integers"
                ))
                return False
        except (ValueError, AttributeError):
            self.errors.append(XMLParseError(
                f"Invalid start_line value '{start_line_elem.text}' in diff {diff_index}, file {file_index}",
                suggestion="start_line must be a valid integer"
            ))
            return False

        return True

    def extract_diffs(self, root: ET.Element) -> List[Dict[str, Any]]:
        """
        Extract diff information from parsed XML.

        Returns:
            List of dictionaries containing file path and diff details
        """
        diffs = []

        if root.tag != 'apply_diff':
            return diffs

        args_elem = root.find('args')
        if args_elem is None:
            return diffs

        for file_elem in args_elem.findall('file'):
            path_elem = file_elem.find('path')
            if path_elem is None or not path_elem.text:
                continue

            file_path = path_elem.text.strip()
            file_diffs = []

            for diff_elem in file_elem.findall('diff'):
                content_elem = diff_elem.find('content')
                start_line_elem = diff_elem.find('start_line')

                if content_elem is not None and start_line_elem is not None:
                    try:
                        start_line = int(start_line_elem.text.strip())
                        content = content_elem.text or ""
                        file_diffs.append({
                            'content': content,
                            'start_line': start_line
                        })
                    except (ValueError, AttributeError):
                        continue

            if file_diffs:
                diffs.append({
                    'path': file_path,
                    'diffs': file_diffs
                })

        return diffs

    def get_error_summary(self) -> str:
        """Get a summary of all errors and warnings."""
        summary = []

        if self.errors:
            summary.append(f"Errors ({len(self.errors)}):")
            for error in self.errors:
                summary.append(f"  - {error}")

        if self.warnings:
            summary.append(f"Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                summary.append(f"  - {warning}")

        return "\n".join(summary) if summary else "No errors or warnings"


def main():
    """Example usage of the XML parser."""
    parser = ApplyDiffXMLParser()

    # Example valid XML
    valid_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<apply_diff>
    <args>
        <file>
            <path>src/main.py</path>
            <diff>
                <content>def hello():
    print("Hello, World!")</content>
                <start_line>1</start_line>
            </diff>
        </file>
    </args>
</apply_diff>'''

    # Example malformed XML
    malformed_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<apply_diff>
    <args>
        <file>
            <path>src/main.py</path>
            <diff>
                <content>def hello():
    print("Hello, World!")</content>
                <start_line>1</start_line>
            </diff>
        </file>
        <file>
            <path>src/utils.py</path>
            <diff>
                <content>def add(a, b):
    return a + b</content>
                <start_line>5</start_line>
            </diff>
            <!-- Missing closing diff tag -->
    </args>
</apply_diff>'''

    print("=== Testing Valid XML ===")
    root = parser.parse_xml_string(valid_xml)
    if root is not None:
        if parser.validate_apply_diff_structure(root):
            diffs = parser.extract_diffs(root)
            print("Successfully parsed valid XML:")
            for diff in diffs:
                print(f"  File: {diff['path']}")
                for d in diff['diffs']:
                    print(f"    Line {d['start_line']}: {d['content'][:50]}...")
        else:
            print("Validation failed:")
            print(parser.get_error_summary())
    else:
        print("Failed to parse XML:")
        print(parser.get_error_summary())

    print("\n=== Testing Malformed XML ===")
    parser2 = ApplyDiffXMLParser()
    root2 = parser2.parse_xml_string(malformed_xml)
    if root2 is not None:
        print("Parsed with recovery:")
        if parser2.validate_apply_diff_structure(root2):
            diffs = parser2.extract_diffs(root2)
            print("Extracted diffs:")
            for diff in diffs:
                print(f"  File: {diff['path']}")
        else:
            print("Validation issues:")
            print(parser2.get_error_summary())
    else:
        print("Failed to parse malformed XML:")
        print(parser2.get_error_summary())


if __name__ == "__main__":
    main()