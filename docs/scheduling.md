# Scheduling the weekly product watch

## What runs

`tools/run_watch.bat` -> `python -m lidl_tracker.cli_watch --query "queso en
salmuera" --to <email>`.

Each run:

1. Discovers currently advertised flyers (both current and next week).
2. Downloads any new PDF (skipped if already present, per `acquisition.py`).
3. Extracts product cards, cached per flyer id (`data/cache/<flyer-id>.json`)
   so a flyer is only ever parsed once, even across many weekly runs.
4. Searches for the query using normalized substring / all-words matching
   (`search.py`) - no LLM.
5. Sends one email per (flyer, query) the first time a match is found,
   tracked in `data/state/watch_state.json` so re-running is a no-op.

If `data/config/smtp.env` is missing or incomplete, the email is printed to
`data/watch.log` instead of sent (dry-run) - safe to leave misconfigured
during setup.

## One-time setup

1. Copy the SMTP config template and fill in real credentials:

   ```
   copy data\config\smtp.env.example data\config\smtp.env
   ```

   For Gmail, `LIDL_SMTP_PASSWORD` must be an App Password (2FA required),
   not the account password.

2. Register the Sunday task (run once, from an elevated or normal prompt):

   ```
   schtasks /create /tn "LidlFlyerWatch" ^
       /tr "\"C:\Users\Jocro\Dev\lidl-flyer-tracker\tools\run_watch.bat\"" ^
       /sc weekly /d SUN /st 09:00 /f
   ```

3. Verify it was created:

   ```
   schtasks /query /tn "LidlFlyerWatch" /v /fo list
   ```

4. Test it immediately without waiting for Sunday:

   ```
   schtasks /run /tn "LidlFlyerWatch"
   type data\watch.log
   ```

## Changing the watched product or recipient

Edit `tools/run_watch.bat` (the `--query` value) or `data\config\smtp.env`
(`LIDL_WATCH_TO`). No task re-registration needed.

## Removing the schedule

```
schtasks /delete /tn "LidlFlyerWatch" /f
```

## Resetting state

To force re-notification for flyers already processed (e.g. after fixing a
parser bug):

```
del data\state\watch_state.json
del data\cache\*.json
```
