/**
 * model-guard.ts — the harness-wide MODEL ALLOWLIST (hard financial guard).
 *
 * Once configured, the harness REFUSES to spawn a child agent for any model that is
 * not on the pre-approved allowlist. Every orchestration path (fh-debate, fh-opinion,
 * fh-fusion, fh-collaborate, fh-auto-validate) funnels through `modelGuardError` in
 * child-runner.ts, so a non-approved model can NEVER make a provider call.
 *
 * Allowlist semantics (case-insensitive):
 *   - a full `provider/id` entry is matched exactly;
 *   - a bare `id` entry (no slash) approves that model id under ANY provider.
 *
 * "Safe by default": if nothing is explicitly pre-approved, the allowlist is EMPTY
 * and every child spawn is blocked — there is no hidden default model.
 */

let locked = false;
const allow = new Set<string>();

function norm(model: string): string {
	return model.trim().toLowerCase();
}

/** Pre-approve an iterable of `provider/id` (or bare `id`) model strings. One-shot. */
export function configureModelGuard(allowed: Iterable<string>): void {
	if (locked) return;
	for (const raw of allowed) {
		const entry = norm(raw);
		if (!entry) continue;
		allow.add(entry);
	}
	locked = true;
}

export function guardLocked(): boolean {
	return locked;
}

export function isModelAllowed(model: string): boolean {
	const n = norm(model);
	if (allow.has(n)) return true;
	// A bare allowlist id (no slash) approves that MODEL ID under any provider:
	// openrouter/deepseek/deepseek-v4-pro is approved by listing `deepseek-v4-pro`.
	const slash = n.lastIndexOf("/");
	if (slash > 0 && allow.has(n.slice(slash + 1))) return true;
	return false;
}

/** Returns a human-facing error when the model is blocked, else undefined. */
export function modelGuardError(model: string, context: string): string | undefined {
	if (isModelAllowed(model)) return undefined;
	const entries = [...allow].join(", ") || "(allowlist is empty — nothing is pre-approved)";
	return (
		`fusion-harness: BLOCKED ${context} — model ${JSON.stringify(model)} is NOT on the approved allowlist. ` +
		`Current allowlist: ${entries}. Pre-approve it via --fh-allow-models / FH_ALLOWED_MODELS or by declaring it in the stack YAML.`
	);
}
