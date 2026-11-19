# Port plan: STORY NAME

Windmill folder: `f/my_folder`. Source: `story.json`.

One line per workflow: `id | flow_name | entry point | size | status`.
Status is `TODO`, `DONE`, or `SKIP: reason` (`SKIP: DISABLED`, `SKIP: no entry point`, `SKIP: no effect`).
A workflow with several cron lines has one line; separate the cron lines with `;`.
A sub-story that workflows call has one line with its planned flow path.

```
w01 | sync_open_items | schedule 15 6 * * * Europe/Dublin; 0 12 * * 6 Europe/Dublin | 7 actions | TODO
w02 | record_item | webhook post | 3 actions | TODO
w03 | request_item | page fields title, day | 4 actions | TODO
w04 | old_report | schedule 0 3 * * * Europe/Dublin | 9 actions | SKIP: DISABLED
s1 | send_message | f/my_folder/send_message | called by 2 workflows | TODO
```

Not triggered (no entry point, not ported): a40 > a41; a42.

Open questions for the user:

- The definition of the lambda `RESOURCE.text_tools.shorten` (used by w02).
- The export of the story `STORY.print_label` (called by w03, not in this export).
