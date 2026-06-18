# Pwn Offset Fixture

This safe synthetic pwn fixture models a stack overwrite puzzle without a real vulnerable binary.

The task is to inspect `transcript.txt`, identify the cyclic crash marker, compute the offset
from the provided pattern index, and assemble the local flag from the recorded proof fields.
No exploit should be executed and no remote service exists.
