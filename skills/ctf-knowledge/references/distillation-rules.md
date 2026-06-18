# Distillation Rules

Turn sources into compact operational knowledge.

## Good Distillation

- Signal -> decision -> first command.
- Tool failure -> diagnosis -> retry.
- Vulnerability clue -> minimal test -> proof requirement.
- File type -> extraction order -> stop condition.
- Paper idea -> benchmarkable skill behavior.

## Bad Distillation

- Whole writeup pasted into SKILL.md.
- Huge payload dictionary without routing.
- Exploit code copied without audit.
- Claim without local verification.
- Long prose that does not alter the next action.

## Reference Size

Keep SKILL.md under 500 lines when possible. Move long details into references with clear "read when" instructions.

## Conversion Examples

Use the phrase "Skill conversion" when recording how a source becomes a reusable skill behavior. A good Skill conversion identifies the trigger signal, the next action, the proof gate, and the reference or script that should be updated.

Writeup says: "Flask debug PIN can be recovered from machine-id and MAC."

Convert to:

- Signal: Flask Werkzeug debug console exposed.
- First check: confirm console page and version.
- Needed files: `/etc/machine-id`, `/proc/sys/kernel/random/boot_id`, MAC source, username/module path if readable.
- Proof: derive PIN and access console inside challenge scope.

Do not paste every historical Flask PIN exploit variant into the master skill.
