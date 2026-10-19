# Worked example (hand-made)

The worked example for [the segmenting guide](../segmenting.md).

| File | What |
|---|---|
| [`sentence.txt`](sentence.txt) | the raw sentence: 昨日、京都の友達から手紙を受け取りました。 ("Yesterday I received a letter from a friend in Kyoto.") |
| [`hand-made-input.json`](hand-made-input.json) | the tsubu input for it |

**Everything in `hand-made-input.json` was made by hand.** No analyser, aligner or model was run
to produce it. The bunsetsu and the readings are what the guide's steps 1 and 2 should give for
this sentence. **The times are invented**: there is no recording of this sentence, and they were
chosen only to show the shape of a timed input (a pause after 、, segments that meet end to start,
half-open spans). Do not use them as a reference for how long anything takes to say.

Check it with the validator from the repository root:

```sh
node docs/agents/validate.mjs docs/agents/example/hand-made-input.json --text docs/agents/example/sentence.txt
```

`tests/test_agent_guide.py` runs the same check, and checks that the validator refuses broken
copies of the example.
