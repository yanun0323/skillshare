#!/usr/bin/env node
import { convert } from "../agents_convert_tool/md-toml.js";

convert(({ body, frontmatter, stem }) => {
    const name = (frontmatter.name || stem).trim();
    const description = (frontmatter.description || "").trim();
    const developerInstructions = body.trim();

    if (!name) {
        throw new Error(
            "claude-agents: missing required field 'name' (Claude custom agents require name)"
        );
    }
    if (!description) {
        throw new Error(
            "claude-agents: missing required frontmatter 'description' (Claude custom agents require description)"
        );
    }
    if (!developerInstructions) {
        throw new Error(
            "claude-agents: missing required markdown body (Claude custom agents require developer_instructions)"
        );
    }

    Object.assign(frontmatter, frontmatter.claude);

    return {
        ...frontmatter,
        developerInstructions: developerInstructions,
        outputType: "claude",
    };
});
