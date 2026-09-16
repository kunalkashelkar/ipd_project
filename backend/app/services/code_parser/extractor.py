# ============================================================
# Function / Method Extractor — AST and Language-Aware Extraction
# ============================================================

from __future__ import annotations

import ast
import hashlib
import re
from typing import TypedDict

from backend.app.services.code_parser.normalizer import normalize_identifiers
from backend.app.services.code_parser.tokenizer import tokenize_code


class ExtractedFunction(TypedDict):
    function_id: str
    qualified_name: str | None
    name: str
    language: str
    start_line: int
    end_line: int
    start_byte: int | None
    end_byte: int | None
    signature: str | None
    original_content_hash: str
    normalized_content_hash: str
    token_count: int
    code: str


def make_function_id(
    snapshot_id: str, relative_path: str, name: str, signature: str | None, start_line: int
) -> str:
    """Compute a deterministic, collision-free semantic function identity within a snapshot."""
    sig = signature or ""
    raw = f"{snapshot_id}:{relative_path}:{name}:{sig}:{start_line}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def extract_python_functions(
    code: str, snapshot_id: str, relative_path: str
) -> list[ExtractedFunction]:
    """Extract functions and methods from Python source using standard library AST."""
    results: list[ExtractedFunction] = []
    lines = code.splitlines(keepends=True)
    byte_offsets: list[int] = [0]
    for line in lines:
        byte_offsets.append(byte_offsets[-1] + len(line.encode("utf-8")))

    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Fallback for Python 2 or code containing syntax errors
        py_pattern = re.compile(
            r"^(?P<indent>[ \t]*)(?:async\s+)?def\s+(?P<name>[a-zA-Z0-9_]+)\s*\((?P<params>[^)]*)\):"
        )
        for idx, line in enumerate(lines):
            m = py_pattern.match(line)
            if not m:
                continue
            indent = len(m.group("indent"))
            func_name = m.group("name")
            params = m.group("params")
            start_line = idx + 1
            end_line = start_line
            for sub_idx in range(idx + 1, len(lines)):
                sub_line = lines[sub_idx]
                if not sub_line.strip() or sub_line.strip().startswith("#"):
                    continue
                sub_indent = len(sub_line) - len(sub_line.lstrip(" \t"))
                if sub_indent <= indent:
                    break
                end_line = sub_idx + 1

            func_lines = lines[idx:end_line]
            func_code = "".join(func_lines)
            start_byte = byte_offsets[idx] if idx < len(byte_offsets) else None
            end_byte = byte_offsets[end_line] if end_line < len(byte_offsets) else None
            sig = f"def {func_name}({params}):"
            orig_hash = hashlib.sha256(func_code.encode("utf-8")).hexdigest()
            _, norm_hash = normalize_identifiers(func_code, language="python", strip_comments=True)
            tok_res = tokenize_code(func_code, language="python")
            fid = make_function_id(snapshot_id, relative_path, func_name, sig, start_line)

            results.append({
                "function_id": fid,
                "qualified_name": func_name,
                "name": func_name,
                "language": "python",
                "start_line": start_line,
                "end_line": end_line,
                "start_byte": start_byte,
                "end_byte": end_byte,
                "signature": sig,
                "original_content_hash": orig_hash,
                "normalized_content_hash": norm_hash,
                "token_count": tok_res.token_count,
                "code": func_code,
            })
        return results

    def _get_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        # Build clean signature string
        args_list = []
        for a in node.args.args:
            args_list.append(a.arg)
        prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
        return f"{prefix}{node.name}({', '.join(args_list)}):"

    def _extract_from_node(node: ast.AST, parent_class: str | None = None):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qname = f"{parent_class}.{child.name}" if parent_class else child.name
                start_line = child.lineno
                end_line = getattr(child, "end_lineno", child.lineno)

                # Extract code slice
                func_lines = lines[start_line - 1 : end_line]
                func_code = "".join(func_lines)

                start_byte = byte_offsets[start_line - 1] if start_line - 1 < len(byte_offsets) else None
                end_byte = byte_offsets[end_line] if end_line < len(byte_offsets) else None

                sig = _get_signature(child)
                orig_hash = hashlib.sha256(func_code.encode("utf-8")).hexdigest()
                _, norm_hash = normalize_identifiers(func_code, language="python", strip_comments=True)
                tok_res = tokenize_code(func_code, language="python")

                fid = make_function_id(snapshot_id, relative_path, child.name, sig, start_line)

                results.append({
                    "function_id": fid,
                    "qualified_name": qname,
                    "name": child.name,
                    "language": "python",
                    "start_line": start_line,
                    "end_line": end_line,
                    "start_byte": start_byte,
                    "end_byte": end_byte,
                    "signature": sig,
                    "original_content_hash": orig_hash,
                    "normalized_content_hash": norm_hash,
                    "token_count": tok_res.token_count,
                    "code": func_code,
                })

            elif isinstance(child, ast.ClassDef):
                _extract_from_node(child, parent_class=child.name)

    _extract_from_node(tree)
    return results


def extract_brace_language_functions(
    code: str, language: str, snapshot_id: str, relative_path: str
) -> list[ExtractedFunction]:
    """Robust syntax and brace-matching function extractor for C/C++/Java/JS/TS/Go/Rust/C#/PHP."""
    results: list[ExtractedFunction] = []
    lines = code.splitlines(keepends=True)
    if not lines:
        return results

    # Line-to-byte offset mapping
    byte_offsets: list[int] = [0]
    for line in lines:
        byte_offsets.append(byte_offsets[-1] + len(line.encode("utf-8")))

    is_js_family = language.lower() in ("javascript", "typescript")

    # Declaration regex patterns by language family
    if is_js_family:
        decl_patterns = [
            # 0: var/let/const name = function(...) or (...) =>
            (
                re.compile(r"(?:var|let|const)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s+)?function\s*(?:[a-zA-Z0-9_$]+)?\s*\(([^)]*)\)"),
                "var_func",
            ),
            (
                re.compile(r"(?:var|let|const)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s+)?(?:\(([^)]*)\)|[a-zA-Z0-9_$]+)\s*=>"),
                "var_arrow",
            ),
            # 1: Standard function name(args)
            (
                re.compile(r"(?:^|[\s,(=])(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(([^)]*)\)"),
                "named_func",
            ),
            # 2: Anonymous function(args) in calls or returns
            (
                re.compile(r"(?:^|[\s,(=])(?:async\s+)?function\s*\(([^)]*)\)"),
                "anon_func",
            ),
            # 3: Arrow callback (args) =>
            (
                re.compile(r"(?:^|[\s,(=])(?:async\s+)?\(([^)]*)\)\s*=>"),
                "arrow_cb",
            ),
            # 4: Object / class method: name(args)
            (
                re.compile(r"^\s*(?:(?:public|private|protected|static|async)\s+)*([a-zA-Z0-9_$]+)\s*\(([^)]*)\)"),
                "method",
            ),
        ]
    else:
        decl_patterns = [
            # Standard: return_type func_name(args)
            (
                re.compile(
                    r"^\s*(?:(?:public|private|protected|static|final|native|synchronized|abstract|export|async|virtual|inline|override)\s+)*"
                    r"(?:[\w<>\[\],\s\*&]+?\s+)?"
                    r"([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(([^)]*)\)\s*(?:const)?\s*(?:throws\s+[\w\s,]+)?"
                ),
                "c_style",
            ),
            # Go: func (r Receiver) Name(args)
            (re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\(([^)]*)\)"), "go"),
            # Rust: fn name(args)
            (re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([a-zA-Z0-9_]+)\s*(?:<[^>]+>)?\s*\(([^)]*)\)"), "rust"),
            # PHP: function name(args)
            (re.compile(r"^\s*(?:(?:public|private|protected|static|async)\s+)*function\s+([a-zA-Z0-9_$]+)\s*\(([^)]*)\)"), "php"),
        ]

    for line_idx, line in enumerate(lines):
        for pattern, kind in decl_patterns:
            match = pattern.search(line)
            if not match:
                continue

            if kind in ("var_func", "var_arrow"):
                func_name = match.group(1)
                sig_line = match.group(0).strip()
            elif kind == "named_func":
                func_name = match.group(1)
                sig_line = f"function {func_name}({match.group(2)})"
            elif kind == "anon_func":
                prefix = line[:match.start()].strip()
                caller = re.search(r"([a-zA-Z0-9_$.]+)\s*\($", prefix)
                if caller:
                    func_name = f"{caller.group(1).split('.')[-1]}$callback"
                else:
                    func_name = f"anonymous_L{line_idx + 1}"
                sig_line = f"function({match.group(1)})"
            elif kind == "arrow_cb":
                prefix = line[:match.start()].strip()
                caller = re.search(r"([a-zA-Z0-9_$.]+)\s*\($", prefix)
                if caller:
                    func_name = f"{caller.group(1).split('.')[-1]}$arrow"
                else:
                    func_name = f"arrow_L{line_idx + 1}"
                sig_line = f"({match.group(1)}) =>"
            elif kind in ("method", "c_style", "go", "rust", "php"):
                func_name = match.group(1)
                # Filter out control statements and keywords
                if func_name in ("if", "for", "while", "switch", "catch", "return", "require", "import", "using"):
                    continue
                sig_line = line.strip()

            # Locate opening brace '{' on this line or subsequent lines (supporting Allman style)
            brace_line_idx = -1
            open_brace_idx = -1

            rest_of_line = line[match.end():]
            idx_in_rest = rest_of_line.find("{")
            if idx_in_rest != -1:
                brace_line_idx = line_idx
                open_brace_idx = match.end() + idx_in_rest
            else:
                for lookahead in range(1, 4):
                    if line_idx + lookahead < len(lines):
                        nxt = lines[line_idx + lookahead]
                        found_pos = nxt.find("{")
                        if found_pos != -1:
                            brace_line_idx = line_idx + lookahead
                            open_brace_idx = found_pos
                            break
                        if nxt.strip():
                            break

            if brace_line_idx == -1 or open_brace_idx == -1:
                continue

            # Trace matching closing brace
            brace_depth = 1
            end_line_idx = brace_line_idx
            in_string = False
            quote_char = ""
            in_block_comment = False

            curr_slice = lines[brace_line_idx][open_brace_idx + 1 :]
            scan_lines = [curr_slice] + lines[brace_line_idx + 1 :]

            found_close = False
            for offset, s_line in enumerate(scan_lines):
                i = 0
                while i < len(s_line):
                    ch = s_line[i]

                    if in_block_comment:
                        if ch == "*" and i + 1 < len(s_line) and s_line[i + 1] == "/":
                            in_block_comment = False
                            i += 2
                            continue
                    elif in_string:
                        if ch == quote_char and (i == 0 or s_line[i - 1] != "\\"):
                            in_string = False
                    else:
                        if ch in ('"', "'", "`"):
                            in_string = True
                            quote_char = ch
                        elif ch == "/" and i + 1 < len(s_line) and s_line[i + 1] == "*":
                            in_block_comment = True
                            i += 2
                            continue
                        elif ch == "/" and i + 1 < len(s_line) and s_line[i + 1] == "/":
                            break
                        elif ch == "{":
                            brace_depth += 1
                        elif ch == "}":
                            brace_depth -= 1
                            if brace_depth == 0:
                                end_line_idx = brace_line_idx + offset
                                found_close = True
                                break
                    i += 1

                if found_close:
                    break

            if found_close:
                start_line = line_idx + 1
                end_line = end_line_idx + 1
                func_lines = lines[line_idx : end_line_idx + 1]
                func_code = "".join(func_lines)

                start_byte = byte_offsets[line_idx] if line_idx < len(byte_offsets) else None
                end_byte = byte_offsets[end_line] if end_line < len(byte_offsets) else None

                orig_hash = hashlib.sha256(func_code.encode("utf-8")).hexdigest()
                _, norm_hash = normalize_identifiers(func_code, language=language, strip_comments=True)
                tok_res = tokenize_code(func_code, language=language)

                fid = make_function_id(snapshot_id, relative_path, func_name, sig_line, start_line)

                results.append({
                    "function_id": fid,
                    "qualified_name": func_name,
                    "name": func_name,
                    "language": language,
                    "start_line": start_line,
                    "end_line": end_line,
                    "start_byte": start_byte,
                    "end_byte": end_byte,
                    "signature": sig_line.rstrip("{").strip(),
                    "original_content_hash": orig_hash,
                    "normalized_content_hash": norm_hash,
                    "token_count": tok_res.token_count,
                    "code": func_code,
                })
                break

    return results


def extract_functions(
    code: str, language: str | None, snapshot_id: str, relative_path: str
) -> list[ExtractedFunction]:
    """High-level function extractor routing to appropriate language extractor."""
    if not language or not code.strip():
        return []

    lang = language.lower()
    if lang == "python":
        return extract_python_functions(code, snapshot_id, relative_path)
    elif lang in ("c", "cpp", "java", "javascript", "typescript", "go", "rust", "csharp", "php"):
        return extract_brace_language_functions(code, lang, snapshot_id, relative_path)

    return []
