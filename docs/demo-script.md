# Interactive demo guide

Open the [five-step demo](https://shiftmate-web-fucvnupudq-de.a.run.app/#demo).
The legacy `#reviewer` entry also works. This guide describes the current
source revision; the hosted rollout may briefly lag the repository.

1. Expand the six-shift ledger. Verify 40 paid hours at NT$200/hour, NT$8,000,
   and the overnight calculation: 8 hours minus 0.5 hour break = 7.5.
2. Compare the synthetic input image and draft. Correct September 9 to 13:00.
   Note that format validation is not confirmation. Simulate confirmation;
   no database write occurs.
3. Switch to conflicting policies. Both synthetic excerpts remain visible:
   six days in version A and four in version B. The answer is refused because
   precedence cannot be determined.
4. Compare the hybrid question and write request. The trace is explicitly
   simulated. The write request calls no data tool and changes no schedule.
5. Follow the isolation, integration and evaluation links. The OCR/RAG/routing
   evaluations have 9/5/12 synthetic cases and 3/1/2 failures respectively;
   inspect their methods and limitations, not just the headline metrics.

Previous/next and direct step navigation retain in-memory choices. Replay
resets correction, confirmation, policy and assistant presets, and ledger
expansion. No live upload, AI, Calendar, schedule read/write or persistent
storage is part of the five-step demo.

The optional authenticated workspace is separate. Its API health indicator
does not gate the synthetic experience.
