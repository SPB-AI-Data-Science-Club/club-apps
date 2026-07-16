# Club games (not yet wired into the portal)

Self-contained activities for club meetings. Nothing here is deployed or linked from the members
portal yet — these files just sit in the repo, ready to use. `jeopardy.html` runs entirely offline
in a browser (no server, no internet), so you can open it on a projector during a meeting.

## Jeopardy (`jeopardy.html`)

Team vs team vocabulary/review game with a classic Jeopardy board, live scoreboard, and Daily Doubles.

**To run it now:** double-click `jeopardy.html` (or open it in any browser). Pick a question set, name
the teams, hit Start. Click a tile to show the clue, press Space to reveal the answer, then click the
team that got it right (or "No one"). The winning team picks the next tile. Board complete = winner screen.

**Two question sets are built in** (Machine Learning Basics, Python and Data Wrangling). More can be added
two ways:

1. **Embedded** — edit the `EMBEDDED_SETS` array at the top of the `<script>` in `jeopardy.html`.
2. **Loaded at runtime** — click "Load custom set (.json)" on the setup screen and pick a `.json` file.
   This is the easiest path for per-meeting sets: the game engine never changes, you just hand it a new file.

### Set format

See `sets/EXAMPLE-neural-networks.json` for a full working example. Structure:

```json
{
  "title": "Topic name shown in the picker",
  "categories": [
    {
      "name": "Category header (kept short, shows on the board)",
      "clues": [
        { "value": 100, "clue": "The statement players read.", "answer": "What is the correct response?" },
        { "value": 400, "clue": "...", "answer": "...", "dd": true }
      ]
    }
  ]
}
```

- `clue` = what the board shows (a statement or definition).
- `answer` = the correct response. Jeopardy phrases these as a question ("What is ...?"), but anything works.
- `dd` (optional) = mark a tile a Daily Double: the picking team wagers before seeing the clue, right adds
  the wager and wrong subtracts it.
- A standard board is 5 categories x 5 clues (values 100–500), but the engine handles any size.

### Making a set for a meeting

Tell Claude Code the meeting topic (e.g. "next meeting is on decision trees") and it can generate a
matching `sets/<topic>.json` you load at game time — no code changes needed.
