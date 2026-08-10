import { basename, extname } from "path";

function block(value) {
    return { type: "block", value };
}

export function convert(mapFields) {
    readStdin().then((input) => {
        const doc = parseMarkdown(input);
        const { developerInstructions, outputType, ...headers } = mapFields(doc) || {};

        delete headers.codex;
        delete headers.claude;

        var lines = [];
        switch (outputType.trim()) {
            case "codex":
            case "gpt":
                lines = output_codex(developerInstructions, headers);
                break;
            default:
                lines = output_claude(developerInstructions, headers);
                break;
        }
        process.stdout.write(lines.join("\n") + (lines.length ? "\n" : ""));
    }).catch((err) => {
        process.stderr.write((err && err.message ? err.message : String(err)) + "\n");
        process.exit(1);
    });
}

function output_claude(developerInstructions, headers) {
    const lines = [];
    lines.push(`---`);
    const visibleHeaders = Object.fromEntries(
        Object.entries(headers).filter(([, value]) => value != null && value !== "")
    );
    if (Object.keys(visibleHeaders).length) lines.push(serializeYaml(visibleHeaders));
    lines.push(`---`);
    lines.push(`${developerInstructions}`);
    return lines;
}

function output_codex(developerInstructions, headers) {
    const lines = [];
    for (const [key, value] of Object.entries(headers)) {
        if (value == null || value === "") continue;
        lines.push(`${key} = ${tomlString(value)}`);
    }
    lines.push(`developer_instructions = ${tomlBlock(developerInstructions)}`);
    return lines;
}

function serializeYaml(headers) {
    if (!isPlainObject(headers)) {
        throw new TypeError("YAML headers must be a plain object");
    }
    return serializeYamlNode(headers, 0, new Set()).join("\n");
}

function serializeYamlNode(value, indent, ancestors) {
    const padding = " ".repeat(indent);
    if (!Array.isArray(value) && !isPlainObject(value)) {
        return [`${padding}${formatYamlScalar(value)}`];
    }
    if (ancestors.has(value)) throw new TypeError("YAML headers cannot contain circular references");

    ancestors.add(value);
    try {
        if (Array.isArray(value)) return serializeYamlSequence(value, indent, ancestors);
        return serializeYamlMapping(value, indent, ancestors);
    } finally {
        ancestors.delete(value);
    }
}

function serializeYamlMapping(value, indent, ancestors) {
    const entries = Object.entries(value);
    if (!entries.length) return [`${" ".repeat(indent)}{}`];

    const padding = " ".repeat(indent);
    const lines = [];
    for (const [key, child] of entries) {
        const prefix = `${padding}${formatYamlKey(key)}:`;
        if (!Array.isArray(child) && !isPlainObject(child)) {
            lines.push(`${prefix} ${formatYamlScalar(child)}`);
            continue;
        }
        if (child.length === 0 || Object.keys(child).length === 0) {
            lines.push(`${prefix} ${Array.isArray(child) ? "[]" : "{}"}`);
            continue;
        }
        lines.push(prefix);
        lines.push(...serializeYamlNode(child, indent + 2, ancestors));
    }
    return lines;
}

function serializeYamlSequence(value, indent, ancestors) {
    if (!value.length) return [`${" ".repeat(indent)}[]`];

    const padding = " ".repeat(indent);
    const lines = [];
    for (const child of value) {
        if (!Array.isArray(child) && !isPlainObject(child)) {
            lines.push(`${padding}- ${formatYamlScalar(child)}`);
            continue;
        }
        if (child.length === 0 || Object.keys(child).length === 0) {
            lines.push(`${padding}- ${Array.isArray(child) ? "[]" : "{}"}`);
            continue;
        }

        const childLines = serializeYamlNode(child, indent + 2, ancestors);
        if (isPlainObject(child)) {
            lines.push(`${padding}- ${childLines[0].slice(indent + 2)}`);
            lines.push(...childLines.slice(1));
        } else {
            lines.push(`${padding}-`);
            lines.push(...childLines);
        }
    }
    return lines;
}

function formatYamlKey(value) {
    return isSafeYamlPlainString(value) ? value : JSON.stringify(value);
}

function formatYamlScalar(value) {
    if (value === null) return "null";
    if (typeof value === "boolean") return String(value);
    if (typeof value === "number") {
        if (Number.isNaN(value)) return ".nan";
        if (value === Infinity) return ".inf";
        if (value === -Infinity) return "-.inf";
        if (Object.is(value, -0)) return "-0";
        return String(value);
    }
    if (typeof value === "string") {
        return isSafeYamlPlainString(value) ? value : JSON.stringify(value);
    }
    throw new TypeError(`unsupported YAML value type: ${typeof value}`);
}

function isSafeYamlPlainString(value) {
    if (!value || value !== value.trim() || /[\r\n\t]/.test(value)) return false;
    if (/^[\-?:,\[\]{}#&*!|>'"%@`]/.test(value)) return false;
    if (/[:]\s|#|[\[\]{}]/.test(value)) return false;
    if (/^(?:---|\.\.\.|null|~|true|false|yes|no|on|off)$/i.test(value)) return false;
    if (/^[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:e[-+]?[0-9]+)?$/i.test(value)) return false;
    if (/^[-+]?(?:0x[0-9a-f]+|0o[0-7]+|0b[01]+|\.inf|\.nan)$/i.test(value)) return false;
    if (/^[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[Tt ]|$)/.test(value)) return false;
    return true;
}

function isPlainObject(value) {
    if (value === null || typeof value !== "object") return false;
    const prototype = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
}

function parseMarkdown(input) {
    const { frontmatterText, body } = splitFrontmatter(input);
    const relPath = process.env.SS_REL_PATH || "input.md";

    return {
        body,
        frontmatter: parseFrontmatter(frontmatterText),
        relPath,
        stem: basename(relPath, extname(relPath)),
    };
}

function splitFrontmatter(input) {
    const match = input.match(/^---\r?\n([\s\S]*?)\r?\n---[ \t]*\r?\n?/);
    if (!match) return { frontmatterText: "", body: input };

    return {
        frontmatterText: match[1],
        body: input.slice(match[0].length),
    };
}

function parseFrontmatter(text) {
    const lines = tokenizeFrontmatter(text);
    if (!lines.length) return {};
    if (lines[0].indent !== 0) {
        throw frontmatterError(lines[0], "top-level fields must not be indented");
    }

    const result = parseBlock(lines, 0, 0);
    if (result.next !== lines.length) {
        throw frontmatterError(lines[result.next], "unexpected indentation");
    }
    if (Array.isArray(result.value)) {
        throw frontmatterError(lines[0], "the frontmatter root must be an object");
    }
    return result.value;
}

function tokenizeFrontmatter(text) {
    const lines = [];
    for (const [index, rawLine] of text.split(/\r?\n/).entries()) {
        const leading = rawLine.match(/^[ \t]*/)[0];
        if (leading.includes("\t")) {
            throw new Error(`invalid frontmatter at line ${index + 1}: tabs cannot be used for indentation`);
        }
        const content = stripYamlComment(rawLine.slice(leading.length)).trimEnd();
        if (!content.trim()) continue;
        lines.push({ indent: leading.length, content, number: index + 1 });
    }
    return lines;
}

function parseBlock(lines, start, indent) {
    if (lines[start].indent !== indent) {
        throw frontmatterError(lines[start], `expected ${indent} spaces of indentation`);
    }
    return lines[start].content === "-" || lines[start].content.startsWith("- ")
        ? parseSequence(lines, start, indent)
        : parseMapping(lines, start, indent);
}

function parseMapping(lines, start, indent) {
    const value = {};
    let next = start;

    while (next < lines.length && lines[next].indent === indent) {
        const line = lines[next];
        if (line.content === "-" || line.content.startsWith("- ")) break;

        const entry = splitMappingEntry(line.content);
        if (!entry) throw frontmatterError(line, "expected a key followed by ':'");
        const key = parseKey(entry.key, line);
        next += 1;

        if (entry.rawValue !== "") {
            value[key] = parseScalar(entry.rawValue, line);
            continue;
        }

        if (next < lines.length && lines[next].indent > indent) {
            const child = parseBlock(lines, next, lines[next].indent);
            value[key] = child.value;
            next = child.next;
        } else if (
            next < lines.length &&
            lines[next].indent === indent &&
            (lines[next].content === "-" || lines[next].content.startsWith("- "))
        ) {
            // YAML permits a sequence belonging to a mapping key to be
            // "indentless", as used by the existing template's tools list.
            const child = parseSequence(lines, next, indent);
            value[key] = child.value;
            next = child.next;
        } else {
            value[key] = null;
        }
    }

    return { value, next };
}

function parseSequence(lines, start, indent) {
    const value = [];
    let next = start;

    while (next < lines.length && lines[next].indent === indent) {
        const line = lines[next];
        if (line.content !== "-" && !line.content.startsWith("- ")) break;

        const itemText = line.content.slice(1).trimStart();
        next += 1;
        if (!itemText) {
            if (next < lines.length && lines[next].indent > indent) {
                const child = parseBlock(lines, next, lines[next].indent);
                value.push(child.value);
                next = child.next;
            } else {
                value.push(null);
            }
            continue;
        }

        const entry = splitMappingEntry(itemText);
        if (!entry) {
            value.push(parseScalar(itemText, line));
            continue;
        }

        const item = {};
        const key = parseKey(entry.key, line);
        if (entry.rawValue !== "") {
            item[key] = parseScalar(entry.rawValue, line);
        } else if (next < lines.length && lines[next].indent > indent) {
            const child = parseBlock(lines, next, lines[next].indent);
            item[key] = child.value;
            next = child.next;
        } else {
            item[key] = null;
        }

        if (next < lines.length && lines[next].indent > indent) {
            const siblings = parseMapping(lines, next, lines[next].indent);
            Object.assign(item, siblings.value);
            next = siblings.next;
        }
        value.push(item);
    }

    return { value, next };
}

function splitMappingEntry(text) {
    const colon = findTopLevelDelimiter(text, ":", true);
    if (colon < 0) return null;
    return {
        key: text.slice(0, colon).trim(),
        rawValue: text.slice(colon + 1).trim(),
    };
}

function parseKey(value, line) {
    if (!value) throw frontmatterError(line, "mapping keys cannot be empty");
    if (value.startsWith(`"`)) return parseDoubleQuoted(value, line);
    if (value.startsWith(`'`)) return parseSingleQuoted(value, line);
    return value;
}

function parseScalar(value, line) {
    if (value.startsWith(`"`)) return parseDoubleQuoted(value, line);
    if (value.startsWith(`'`)) return parseSingleQuoted(value, line);
    if (value.startsWith("[") && value.endsWith("]")) {
        return parseFlowSequence(value.slice(1, -1), line);
    }
    if (value.startsWith("{") && value.endsWith("}")) {
        return parseFlowMapping(value.slice(1, -1), line);
    }
    if (/^(?:null|~)$/i.test(value)) return null;
    if (/^(?:true|false)$/i.test(value)) return value.toLowerCase() === "true";

    const normalized = value.replaceAll("_", "");
    if (/^[-+]?(?:0|[1-9][0-9]*)$/.test(normalized)) return Number(normalized);
    if (/^[-+]?(?:0x[0-9a-f]+|0o[0-7]+|0b[01]+)$/i.test(normalized)) {
        const sign = normalized.startsWith("-") ? -1 : 1;
        const unsigned = normalized.replace(/^[-+]/, "");
        return sign * Number(unsigned);
    }
    if (/^[-+]?(?:(?:[0-9]+\.[0-9]*)|(?:\.[0-9]+)|(?:[0-9]+(?:\.[0-9]*)?[eE][-+]?[0-9]+))$/.test(normalized)) {
        return Number(normalized);
    }
    if (/^[-+]?\.inf$/i.test(value)) return value.startsWith("-") ? -Infinity : Infinity;
    if (/^\.nan$/i.test(value)) return NaN;
    return value;
}

function parseDoubleQuoted(value, line) {
    try {
        const parsed = JSON.parse(value);
        if (typeof parsed !== "string") throw new Error("not a string");
        return parsed;
    } catch {
        throw frontmatterError(line, `invalid double-quoted string: ${value}`);
    }
}

function parseSingleQuoted(value, line) {
    if (value.length < 2 || !value.endsWith(`'`)) {
        throw frontmatterError(line, `invalid single-quoted string: ${value}`);
    }
    return value.slice(1, -1).replaceAll(`''`, `'`);
}

function parseFlowSequence(content, line) {
    if (!content.trim()) return [];
    return splitFlowItems(content, line).map((item) => parseScalar(item, line));
}

function parseFlowMapping(content, line) {
    const value = {};
    if (!content.trim()) return value;
    for (const item of splitFlowItems(content, line)) {
        const entry = splitMappingEntry(item);
        if (!entry) throw frontmatterError(line, `invalid flow mapping entry: ${item}`);
        value[parseKey(entry.key, line)] = parseScalar(entry.rawValue, line);
    }
    return value;
}

function splitFlowItems(content, line) {
    const items = [];
    let start = 0;
    while (start < content.length) {
        const comma = findTopLevelDelimiter(content, ",", false, start);
        const end = comma < 0 ? content.length : comma;
        const item = content.slice(start, end).trim();
        if (!item) throw frontmatterError(line, "flow collections cannot contain empty items");
        items.push(item);
        if (comma < 0) break;
        start = comma + 1;
    }
    return items;
}

function findTopLevelDelimiter(text, delimiter, requireFollowingSpace, from = 0) {
    let quote = "";
    let escaped = false;
    let depth = 0;
    for (let index = from; index < text.length; index += 1) {
        const char = text[index];
        if (quote) {
            if (quote === `"` && char === "\\" && !escaped) {
                escaped = true;
                continue;
            }
            if (char === quote && !escaped) quote = "";
            escaped = false;
            continue;
        }
        if (char === `"` || char === `'`) {
            quote = char;
            continue;
        }
        if (char === "[" || char === "{") depth += 1;
        else if (char === "]" || char === "}") depth -= 1;
        else if (
            depth === 0 &&
            char === delimiter &&
            (!requireFollowingSpace || index + 1 === text.length || /\s/.test(text[index + 1]))
        ) {
            return index;
        }
    }
    return -1;
}

function stripYamlComment(text) {
    let quote = "";
    let escaped = false;
    for (let index = 0; index < text.length; index += 1) {
        const char = text[index];
        if (quote) {
            if (quote === `"` && char === "\\" && !escaped) {
                escaped = true;
                continue;
            }
            if (char === quote && !escaped) quote = "";
            escaped = false;
            continue;
        }
        if (char === `"` || char === `'`) quote = char;
        else if (char === "#" && (index === 0 || /\s/.test(text[index - 1]))) return text.slice(0, index);
    }
    return text;
}

function frontmatterError(line, message) {
    return new Error(`invalid frontmatter at line ${line.number}: ${message}`);
}

function tomlString(value) {
    // JSON basic-string escaping is a valid subset of TOML basic strings and,
    // unlike a hand-rolled escape of just \ and ", also handles control
    // characters (newlines, tabs, etc.) that would otherwise produce invalid TOML.
    return JSON.stringify(String(value));
}

function tomlBlock(value) {
    const text = String(value).replace(/\n+$/, "");
    if (!text.includes(`"""`)) return `"""\n${text}\n"""`;
    if (!text.includes(`'''`)) return `'''\n${text}\n'''`;
    return `"""\n${text.replace(/"""/g, `\\"""`)}\n"""`;
}

function readStdin() {
    return new Promise((resolve) => {
        let data = "";
        process.stdin.setEncoding("utf8");
        process.stdin.on("data", (chunk) => (data += chunk));
        process.stdin.on("end", () => resolve(data));
    });
}

export default { block, convert, parseFrontmatter, serializeYaml };
