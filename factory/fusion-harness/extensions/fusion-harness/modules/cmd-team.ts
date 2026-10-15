/**
 * TEAM MODE — talk to the team in plain English. No /fh-* commands required.
 *
 * Nick's requirement (2026-10-15): "I should not have to CODE to talk to a team of AIs.
 * They need to think like me and obey me." He has README-FIRST.md — the briefing is on disk.
 *
 * Behaviour: when team mode is ON, every plain (non-slash) message he types fans out to every
 * configured slot, each answering in its own assigned role. The ARCHITECT then fuses the five
 * answers into ONE reply addressed to Nick — a single voice, not a wall of five.
 *
 * Roles never need naming. He types English; the architect decides who does what.
 */
import * as fs from "node:fs";
import * as path from "node:path";
import { runChild } from "./child-runner.ts";
import {
	CUSTOM_TYPE,
	runOk,
	runError,
	toStat,
	truncateChars,
	type AgentRun,
	type HarnessDeps,
} from "./runtime.ts";

/** Team-mode system preface: every slot gets this ON TOP of its role contract. */
/**
 * Team members get bash IN ADDITION to read-only file tools. They need it to reach the live
 * databases (psql over ssh to n100) and to prove things — the whole point of the spec-validator
 * role is checking against the URS table, and that table is in Postgres, not in a file.
 *
 * Safety is carried by the CONTRACT, not by the tool allowlist: every role contract forbids
 * writing (no rm, no move, no markdown in the factory, never touch ~/librechat, mcp_shell.py,
 * pg_hba.conf or the live tunnels). The shell MCP separately blocks write-verb + system-path
 * commands. Members are also instructed to correct nothing without Nick's approval, so a
 * read-only stance is the default behaviour even with bash available.
 */
export const TEAM_MEMBER_TOOLS = "read,grep,find,ls,bash";

/**
 * Two budgets, because a chat turn and a work turn are not the same job.
 *
 *   CHAT  (2.5 min)  — "hello team", "what does this app do?", "state your role".
 *                      Reading a file or two. Nick is standing there waiting for a sentence.
 *   WORK  (5 min)    — "read this app and fill out the spec row", "propose the features",
 *                      "wire up the TV view". Members must read several files, query
 *                      Postgres over ssh, and think. A tight cap here just kills real work:
 *                      the 2.5 min cap timed out the code expert on a SINGLE 25 KB file read.
 *
 * On expiry the member is marked failed and the turn proceeds with the survivors — a slow
 * model never holds the whole reply hostage.
 *
 * (The harness-wide --child-timeout default is 8 HOURS, right for `/fh-auto-validate` building
 * for hours, and useless for a conversation. These caps are team mode's own.)
 */
/**
 * TEAM TRANSCRIPTS — a permanent development trail.
 *
 * The harness's own artifact dirs are mkdtemp under /tmp: random names, cleared on a restart
 * of the box. Nick (2026-10-15): "that way you can summarize it and ask me questions, and we
 * can have a development trail." So every team turn ALSO writes a dated, readable folder here,
 * and the reply is mirrored to a single file he can open any time.
 *
 * Layout:
 *   /home/taza/repo/factory/team-log/<YYYY-MM-DD>/<HHMMSS>-<slug>/
 *       prompt.md      what Nick asked
 *       reply.md       the architect's ONE fused reply (the thing Nick reads)
 *       <slot>.md      each member's own answer, for the trail
 *       meta.json      timing, cost, models, statuses
 *   /home/taza/repo/factory/team-log/LATEST-reply.md   the most recent reply
 */
const TEAM_LOG_ROOT = "/home/taza/repo/factory/team-log";

const TEAM_CHAT_MEMBER_TIMEOUT_MS = 150_000; // 2.5 min
const TEAM_WORK_MEMBER_TIMEOUT_MS = 600_000; // 10 min — real spec work reads the repo AND queries the live table

/** The architect's fusion turn is one synthesis over already-gathered material — cap it tighter. */
const TEAM_CHAT_FUSE_TIMEOUT_MS = 120_000; // 2 min
const TEAM_WORK_FUSE_TIMEOUT_MS = 300_000; // 5 min — a work reply is longer than a chat reply

/**
 * Is this a WORK turn or a CHAT turn?
 *
 * Deterministic on purpose. A model call to classify would cost a turn and could misclassify;
 * this is a keyword check over Nick's own phrasing. It errs toward WORK when it is unsure,
 * because the cost of a too-long timeout is a slower reply, while the cost of a too-short one
 * is a member failing mid-task (which is what already happened to the code expert).
 *
 * WORK verbs: read, examine, inspect, look at, review, analyse, build, write, implement, wire,
 *             propose, draft, fill, populate, update, change, fix, deploy, query, check, verify.
 * CHAT is the default only for short greetings/status questions.
 */
const WORK_HINTS = [
	"read", "examine", "inspect", "look at", "review", "analys", "analyz", "study",
	"build", "write", "implement", "wire", "create", "make", "add ", "draft",
	"propose", "fill", "populate", "complete", "update", "change", "fix", "deploy",
	"query", "check", "verify", "test", "compare", "map ", "trace", "find", "search",
	"spec", "table", "database", "schema", "ac/", "vm", "ac_", "prototype", "app",
	"file", "repo", "function", "module", "script", "service", "systemd", "cron",
	"column", "row", "csv", "tsv", "yaml", "json", "psql", "sql", "ssh",
	//
	// Scope/volume words also mean a heavier turn even without a verb.
	"all ", "every", "each", "full", "entire", "entire ", "bootstrap",
];

/** Short greetings are chat unless a work hint is present. */
const CHAT_ONLY = [
	"hello", "hi ", "hey", "good morning", "good afternoon", "good evening",
	"thanks", "thank you", "who are you", "who is present", "your role", "state your role",
	"what is each of your jobs", "are you there", "you there",
];

export function isWorkTurn(text: string): boolean {
	const t = ` ${text.toLowerCase().trim()} `;
	// Greeting with no work verb -> chat.
	const greeting = CHAT_ONLY.some((g) => t.includes(g));
	const work = WORK_HINTS.some((h) => t.includes(h));
	if (work) return true;         // a work hint always wins
	if (greeting) return false;    // pure greeting -> chat
	// Unknown: a long message is usually a task; a short one is usually a remark.
	return text.trim().length > 140;
}


const TEAM_DOCTRINE = `
You are ONE MEMBER OF NICK'S TEAM. He is talking to the whole team at once, in plain English.

THE FIRST RULE: Nick is in charge. You obey him. You do not ask him to learn commands, flags,
syntax, or file names. You do not ask him to paste context. If you need something, go and get it.

THE SECOND RULE: You have the briefing already. Read these yourself, first, without being asked:
  /home/taza/repo/factory/index/index.tsv        — THE REPO INDEX. Read this FIRST, always.
      A broad "find *.py" returns 1,378 paths; you cannot read them, so you would guess.
      The index lists every real source file (331) with a one-line purpose, its host, and the
      spec_ids it references. USE IT TO CHOOSE FILES, then read only those. Columns:
      host, kind, path, purpose, spec_ids, unit, bytes.
      Before you search, grep the index:
        grep -i "checklist" /home/taza/repo/factory/index/index.tsv
      Its "unit" column names the systemd unit that runs a script; the index is regenerated
      hourly, so it is not stale (unlike a hand-written map).
  /home/taza/repo/README-FIRST.md                — the whole structure, equipment and workflow
  the spec database — LIVE, not an export. You have bash; use it:
      ssh taza@192.168.2.102 "psql -d spec -c '<your query>'"
      the URS table is spec.taza_os_user_requirement_specifications (292 rows)
      e.g. to look for a feature:
        ssh taza@192.168.2.102 "psql -d spec -c \"SELECT spec_id,name FROM spec.taza_os_user_requirement_specifications WHERE name ILIKE '%checklist%' OR user_requirement ILIKE '%checklist%';\""
  the decisions database — same box. Query it the same way.
  ALSO read the source of truth in the repo when relevant: product/**, factory/**.
Never say "I could not reach the database" without having TRIED that ssh command. A CSV export
on disk is STALE — if you rely on it, say that you did and that it may be out of date.
The workflow is in his document. Follow it. Do not invent a different one.

THE THIRD RULE: STAY IN YOUR ASSIGNED ROLE. Other members are covering the other angles.
Do the job you were given and nothing else:
  ARCHITECT        — break the work down, name the spec_ids, say what order things go in
  CODE EXPERT      — how it is actually built in this repo; the concrete implementation
  RED TEAM         — what breaks, what silently fails, what is claimed but not proven
  SPEC VALIDATOR   — does this map against the URS specs table; the AC and the VM
  DOCUMENTARIAN    — what gets recorded, and in which database
Do NOT all answer the same way. Your value is your lane.

THE FOURTH RULE: Answer Nick's actual question. Not the question you wish he'd asked.
If he asks "what does the checklist app do?", answer THAT. Do not survey the filesystem,
do not list other stacks, do not give him an inventory he did not ask for.
Be short and concrete. Lead with the answer. If the answer is "I don't know yet, here is
what I need to read", say that in one line — do not pad.

THE FIFTH RULE: Provenance. When you state something from a spec, name the spec_id. When you
state something from a file, name the file. Never invent a table, a column, or a spec_id.
An unproven claim is worse than saying nothing.

THE SIXTH RULE: His review is the loop. He will read, correct you, and approve in plain English.
You do not need permission to read. You DO need his approval before building or changing specs.
When he corrects you, accept it as the decision — record it, do not argue.
`;

export type TeamMode = {
	enabled: boolean;
	set(on: boolean): void;
	/** True when this message should be handled as a team turn. */
	shouldHandle(text: string, source: string): boolean;
};

/** What the architect is asked to produce: ONE reply, in Nick's own terms. */
const FUSE_INSTRUCTION = `You are the ARCHITECT of Nick's team. Your five members have each answered
Nick's message from their own role. Your job now is to give Nick ONE clear reply.

Rules for your reply:
- Speak directly to Nick, as his team. First person plural or first person — whichever reads
  more naturally. Never mention "models", "slots", "agents", "tokens" or the harness.
- Lead with the direct answer to what he asked. No preamble, no "Great question".
- Merge the members' findings into one coherent answer. Drop duplication. Where they disagree,
  say so in one line and give your call.
- Name spec_ids and file paths where the members gave them.
- If the honest answer is "we do not have this yet", say so plainly and say what you need.
- End with ONE short line proposing the next concrete step for his approval. Not a menu.
- Keep it tight. He is reading this on a phone. If it can be three paragraphs, do not write six.`;

export function registerTeamMode(pi: any, h: HarnessDeps, teamMode: TeamMode): void {
	pi.registerCommand("fh-team-mode", {
		description: "Turn plain-English team mode on/off. With it on, every message you type goes to the whole team and one fused answer comes back. Usage: /fh-team-mode [on|off]",
		handler: async (raw: string, ctx: any) => {
			const arg = (raw ?? "").trim().toLowerCase();
			if (arg === "on" || arg === "off") teamMode.set(arg === "on");
			else teamMode.set(!teamMode.enabled);
			ctx.ui.notify(`fusion-harness: team mode ${teamMode.enabled ? "ON — just talk normally" : "OFF — /fh-* commands only"}`, "info");
		},
	});

	pi.on("input", async (event: any, ctx: any) => {
		if (!teamMode.enabled) return { action: "continue" as const };
		if (event.source !== "interactive") return { action: "continue" as const };
		const text = (event.text ?? "").trim();
		if (!text || text.startsWith("/")) return { action: "continue" as const };

		await runTeamTurn(text, ctx, h);
		return { action: "handled" as const };
	});
}

/** Fan out to every slot, then have the architect fuse into one reply for Nick. */
export async function runTeamTurn(prompt: string, ctx: any, h: HarnessDeps): Promise<void> {
	h.noteHost(ctx);

	// One decision at the top: this turn's budget. Chat is quick; work gets room to read the
	// repo and query the database, because a 2.5 min cap killed the code expert on one file read.
	const work = isWorkTurn(prompt);
	const memberTimeoutMs = work ? TEAM_WORK_MEMBER_TIMEOUT_MS : TEAM_CHAT_MEMBER_TIMEOUT_MS;
	const fuseTimeoutMs = work ? TEAM_WORK_FUSE_TIMEOUT_MS : TEAM_CHAT_FUSE_TIMEOUT_MS;
	ctx.ui.setStatus(CUSTOM_TYPE, `team: ${work ? "work" : "chat"} turn (up to ${Math.round(memberTimeoutMs / 60000)} min per member)…`);
	const stack = h.modelStack();
	const slots = stack.slots;
	if (!slots.length) {
		ctx.ui.notify("fusion-harness: no slots configured — team mode has nobody to ask", "error");
		return;
	}

	const startedAt = Date.now();
	const artifactsDir = await h.mkArtifacts();
	await h.save(artifactsDir, "prompt.md", prompt);

	// Durable trail dir. Best-effort: a failure here must NEVER break a turn.
	let trailDir = "";
	try {
		const t = new Date();
		const day = t.toISOString().slice(0, 10);
		const hhmmss = t.toISOString().slice(11, 19).replace(/:/g, "");
		const slug = (prompt.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40)) || "turn";
		trailDir = path.join(TEAM_LOG_ROOT, day, `${hhmmss}-${slug}`);
		await fs.promises.mkdir(trailDir, { recursive: true });
		await h.save(trailDir, "prompt.md", prompt);
	} catch {
		trailDir = "";
	}
	await h.save(artifactsDir, "stack.json", JSON.stringify(stack, null, 2));
	h.panel({ kind: "prompt", command: "team", ok: true }, `team › ${prompt}`);

	const runs: AgentRun[] = slots.map(h.newSlotRun);
	const stopper = h.startStoppable(ctx, "team");
	const stopWidget = h.startGridWidget(ctx, "team", runs, undefined, startedAt);

	try {
		ctx.ui.setStatus(CUSTOM_TYPE, `team: ${runs.length} members thinking…`);

		// ── fan out: every member answers in its own lane ──
		await Promise.all(runs.map(async (run) => {
			const slot = run.slot!;
			const agentDir = path.join(artifactsDir, "agents", slot.id);
			await fs.promises.mkdir(agentDir, { recursive: true });
			await runChild({
				run,
				prompt: `${TEAM_DOCTRINE}\n\n───── NICK SAYS ─────\n${prompt}`,
				systemPrompt: slot.systemPrompt,
				appendSystemPrompts: slot.appendSystemPrompts,
				tools: TEAM_MEMBER_TOOLS,
				thinking: slot.thinking,
				...h.slotInitialSpawn(slot, ctx, agentDir),
				cwd: ctx.cwd,
				timeoutMs: memberTimeoutMs,
				signal: stopper.signal,
			});
			await h.save(agentDir, "answer.md", runOk(run) ? run.text : `FAILED: ${runError(run)}`);
			// the trail keeps each member's own words — that is the audit of who said what
			if (trailDir) {
				try {
					const body = `# ${slot.name} — ${slot.architect ? "ARCHITECT" : slot.primary ? "CODE EXPERT" : "MEMBER"}\n` +
						`model: ${slot.model}\nstatus: ${run.status}\n\n` +
						(runOk(run) ? run.text : `FAILED: ${runError(run)}`) + "\n";
					await h.save(trailDir, `${slot.id}.md`, body);
				} catch { /* trail is best-effort */ }
			}
		}));

		if (stopper.stopped()) {
			h.stoppedPanel("team", runs, artifactsDir, startedAt, "Stopped while the team was thinking; finished answers remain on disk.");
			return;
		}

		const survivors = runs.filter(runOk);
		if (!survivors.length) {
			h.panel(
				{ kind: "error", command: "team", ok: false, sources: runs.map(toStat), artifactsDir, ...h.totals(runs, startedAt) },
				`Nobody on the team could answer:\n${runs.map((r) => `- ${r.slot?.name}: ${runError(r)}`).join("\n")}`,
			);
			return;
		}

		// ── fuse: the architect speaks to Nick with ONE voice ──
		ctx.ui.setStatus(CUSTOM_TYPE, "team: architect is composing one reply…");
		const architectSlot = stack.architect;
		const fuseRun = h.newSlotRun(architectSlot);
		const fuseDir = path.join(artifactsDir, "fused");
		await fs.promises.mkdir(fuseDir, { recursive: true });
		const members = survivors
			.map((run) => `## ${run.slot!.name.toUpperCase()} — ${run.slot!.architect ? "ARCHITECT" : "MEMBER"}\n${truncateChars(run.text, 24_000)}`)
			.join("\n\n");
		// HARD WATCHDOG on the fuse. runChild only settles on the child's `close`/`error` event;
		// if the child never spawns or dies without closing, the await hangs forever and the whole
		// turn wedges with no process alive (observed twice on 2026-10-15). The members' answers are
		// already in hand, so the turn must NEVER depend on the fuser returning.
		let fuseSettled = false;
		const fuseGuard = new Promise<void>((resolve) => {
			setTimeout(() => {
				if (!fuseSettled) {
					fuseRun.status = "timeout";
					fuseRun.errorMessage = "fuse watchdog: no result within budget";
				}
				resolve();
			}, fuseTimeoutMs + 15_000);
		});

		await Promise.race([runChild({
			run: fuseRun,
			prompt: `${FUSE_INSTRUCTION}\n\n───── NICK SAID ─────\n${prompt}\n\n───── WHAT YOUR MEMBERS FOUND ─────\n${members}`,
			systemPrompt: architectSlot.systemPrompt,
			appendSystemPrompts: architectSlot.appendSystemPrompts,
			tools: "none",
			thinking: architectSlot.thinking,
			// The fuser must NEVER resume a session that just died. Observed 2026-10-15: when
			// the architect slot timed out mid-work, the fuse resumed that killed session and
			// wedged — the run sat for 9+ minutes with no child process alive, so Nick's page
			// showed "the architect is stuck" while everyone else was long done.
			// A session is only safe to resume if the architect run that owns it actually
			// COMPLETED. After a timeout/abort/failure, start the fuser on a FRESH session:
			// it already has every member's answer in its prompt, so it needs no history.
			...(() => {
				const initial = h.slotInitialSpawn(architectSlot, ctx, fuseDir);
				const architectRun = runs.find((r) => r.slot?.id === architectSlot.id);
				const resumable = !!architectRun && architectRun.status === "done" && !!architectRun.sessionRef;
				if (!resumable) return initial; // fresh session — the safe default
				return h.slotNextSpawn(architectSlot, fuseRun, initial, ctx);
			})(),
			cwd: ctx.cwd,
			timeoutMs: fuseTimeoutMs,
			signal: stopper.signal,
		}).then(() => { fuseSettled = true; }).catch(() => { fuseSettled = true; }), fuseGuard]);

		// If the fuser failed or wedged, still give Nick the members' own answers rather than nothing.
		const fused = runOk(fuseRun)
			? fuseRun.text
			: `(the architect could not compose a reply: ${runError(fuseRun)})` +
			  `\n\nHere is what the team found, unfused:\n\n${members}`;
		await h.save(fuseDir, "reply.md", fused);
		if (trailDir) {
			try {
				await h.save(trailDir, "reply.md", fused);
				await h.save(TEAM_LOG_ROOT, "LATEST-reply.md", fused);
			} catch { /* trail is best-effort */ }
		}

		// One panel, addressed to Nick — the fused voice on top, member detail beneath.
		h.panel(
			{
				kind: "multi",
				command: "team",
				title: "TEAM › REPLY",
				ok: true,
				prompt,
				sources: runs.map(toStat),
				answers: [
					{ role: "ARCHITECT" as const, model: stack.architect.model, text: fused, slotId: stack.architect.id, slotName: stack.architect.name, color: stack.architect.color, primary: false },
					...survivors.map((run) => ({
						role: run.role,
						model: run.model,
						text: run.text,
						slotId: run.slot!.id,
						slotName: run.slot!.name,
						color: run.slot!.color,
						primary: run.slot!.primary,
					})),
				],
				artifactsDir,
				...h.totals(runs, startedAt),
			},
			fused,
		);

		if (trailDir) {
			try {
				await h.save(trailDir, "meta.json", JSON.stringify({
					when: new Date().toISOString(),
					turn: work ? "work" : "chat",
					prompt,
					fusedBy: stack.architect.name,
					agents: runs.map((r) => ({
						slot: r.slot?.name, role: r.role, model: r.model,
						status: r.status, ms: r.ms, cost: r.costUsd,
					})),
					...h.totals(runs, startedAt),
				}, null, 2));
			} catch { /* trail is best-effort */ }
		}
		await h.save(
			artifactsDir,
			"summary.json",
			JSON.stringify(
				{
					command: "team",
					ok: true,
					prompt,
					agents: runs.map(toStat),
					fusedBy: stack.architect.name,
					sessions: Object.fromEntries(slots.map((slot) => [slot.id, runs.find((r) => r.slot?.id === slot.id)?.sessionRef ?? h.cachedSlotId(slot)])),
					...h.totals(runs, startedAt),
				},
				null,
				2,
			),
		);
	} finally {
		stopper.release();
		stopWidget();
		ctx.ui.setStatus(CUSTOM_TYPE, undefined);
	}
}

/**
 * The welcome Nick sees on load — proves the team is present and says how to use it
 * WITHOUT requiring a command. Rendered as a boot entry, never as LLM context.
 */
export function teamWelcome(h: HarnessDeps): string {
	const stack = h.modelStack();
	const lines = [
		"┌─ YOUR TEAM IS PRESENT ─────────────────────────────────────────────",
		"│ Talk to them in plain English. They will sort out who does what.",
		"│ Nothing to type first. Nothing to prefix. Just say what you want.",
		"│",
	];
	const labels: Record<string, string> = {
		architect: "ARCHITECT   ",
		primary: "CODE EXPERT ",
	};
	for (const slot of stack.slots) {
		const label = slot.architect ? labels.architect : slot.primary ? labels.primary : "MEMBER      ";
		lines.push(`│  ● ${label} ${slot.name}  ·  ${slot.model}`);
	}
	lines.push("│");
	lines.push("│ Try:  \"hello team, let's look at all specs for the checklist app.\"");
	lines.push("│      \"that's wrong — it also needs x, y, z, but I'll accept partial z.\"");
	lines.push("│      \"I like it. Approved for building.\"");
	lines.push("└────────────────────────────────────────────────────────────────────");
	return lines.join("\n");
}
