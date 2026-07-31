#!/usr/bin/env node
import { convert } from "../agents_convert_tool/md-toml.js";

convert(({ body, frontmatter, stem }) => {
    const name = (frontmatter.name || stem).trim();
    const description = (frontmatter.description || "").trim();
    const developerInstructions = body.trim();

    if (!name) {
        throw new Error(
            "codex-agents: missing required field 'name' (Codex custom agents require name)"
        );
    }
    if (!description) {
        throw new Error(
            "codex-agents: missing required frontmatter 'description' (Codex custom agents require description)"
        );
    }
    if (!developerInstructions) {
        throw new Error(
            "codex-agents: missing required markdown body (Codex custom agents require developer_instructions)"
        );
    }

    Object.assign(frontmatter, frontmatter.codex);

    return {
        ...frontmatter,
        developerInstructions: developerInstructions,
        outputType: "codex",
    };
});
