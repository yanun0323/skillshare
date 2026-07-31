const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const path = require("node:path");
const test = require("node:test");

const { parseFrontmatter, serializeYaml } = require("./md-toml.js").default;

test("parseFrontmatter preserves nested mappings, sequences, and scalar types", () => {
    const result = parseFrontmatter(`
name: default
enabled: true
retries: 3
claude:
  model: sonnet
  tools:
    - Read
    - Write
  runtime:
    timeout: 1.5
    optional: null
codex:
  model: gpt-5.3-codex-spark
`);

    assert.deepEqual(result, {
        name: "default",
        enabled: true,
        retries: 3,
        claude: {
            model: "sonnet",
            tools: ["Read", "Write"],
            runtime: {
                timeout: 1.5,
                optional: null,
            },
        },
        codex: {
            model: "gpt-5.3-codex-spark",
        },
    });
});

test("parseFrontmatter handles object sequences and inline collections", () => {
    const result = parseFrontmatter(`
profiles:
  - name: reviewer
    permissions:
      write: false
    tags: [review, "code # quality"]
options: {retries: 2, labels: [safe, fast]}
note: keep # discard this comment
`);

    assert.deepEqual(result, {
        profiles: [
            {
                name: "reviewer",
                permissions: { write: false },
                tags: ["review", "code # quality"],
            },
        ],
        options: { retries: 2, labels: ["safe", "fast"] },
        note: "keep",
    });
});

test("serializeYaml writes nested YAML without losing scalar types", () => {
    const headers = {
        name: "default",
        enabled: true,
        retries: 3,
        tools: ["Read", "Write"],
        runtime: { timeout: 1.5, optional: null },
        profiles: [{ name: "reviewer", permissions: { write: false } }],
        ambiguous: "true",
        message: "first line\nsecond line",
        emptySequence: [],
        emptyMapping: {},
    };
    const result = serializeYaml(headers);

    assert.equal(result, `name: default
enabled: true
retries: 3
tools:
  - Read
  - Write
runtime:
  timeout: 1.5
  optional: null
profiles:
  - name: reviewer
    permissions:
      write: false
ambiguous: "true"
message: "first line\\nsecond line"
emptySequence: []
emptyMapping: {}`);
    assert.deepEqual(parseFrontmatter(result), headers);
});

test("serializeYaml rejects circular and unsupported values", () => {
    const circular = {};
    circular.self = circular;

    assert.throws(() => serializeYaml(circular), /circular references/);
    assert.throws(() => serializeYaml({ missing: undefined }), /unsupported YAML value type/);
});

test("converter applies only the claude child object", () => {
    const input = `---
name: default
description: Test agent
claude:
  model: sonnet
  tools:
    - Read
    - Write
codex:
  model: gpt-5.3-codex-spark
  sandbox_mode: read-only
---
Follow the instructions.
`;
    const result = spawnSync(process.execPath, [path.join(__dirname, "convert.js")], {
        input,
        encoding: "utf8",
        env: { ...process.env, SS_REL_PATH: "default.md" },
    });

    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /^model: sonnet$/m);
    assert.match(result.stdout, /^tools:\n  - Read\n  - Write$/m);
    assert.doesNotMatch(result.stdout, /gpt-5\.3-codex-spark|sandbox_mode/);
});
