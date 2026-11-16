# Lesson library

Start with a series, then open a lesson's `brief.md` to prepare it. Lessons are independent of the presenter and editing experiments; use whichever delivery format serves the goal.

## Series

- [DE for Fun](de-for-fun/README.md): first lesson, [From event to answer](de-for-fun/event-to-answer/brief.md).

## Layout and ownership

```text
lessons/<subject>/README.md                      # series order and status
lessons/<subject>/<lesson-id>/brief.md           # goal, evidence, preparation, media links
lessons/<subject>/<lesson-id>/presenter.json     # optional presenter scenes and narration
lessons/<subject>/<lesson-id>/publishing.md      # platform copy, review, publication record
```

Use stable subject and lesson IDs across scripts, media, and publication records. Copy [the brief template](templates/brief.md) when preparing another lesson; keep unprepared topics in the series index rather than creating empty packages.

Keep narration in the delivery script, not duplicated in the brief. Link technical evidence and prerequisites in the subject repository, recording its commit. Keep lesson preparation and publication records here. Raw footage, takes, and renders stay outside Git; record links according to [asset ownership](../CONTENT_ASSETS.md).

The presenter can import portable JSON manually. Its bundled starter is served from this library; no subject application is required to start the studio.
