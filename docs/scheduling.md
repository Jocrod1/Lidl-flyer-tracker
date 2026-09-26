# Scheduling the product watch

## GitHub Actions schedule

The **Lidl Flyer Watch** workflow runs at 08:00 and 18:00 UTC on Sundays and
Mondays (four checks per week). GitHub Actions cron uses UTC; these times are
approximately 09:00/19:00 in mainland Spain during winter and 10:00/20:00
during summer. GitHub may delay scheduled runs under load.

The multiple checks are an intentional, limited strategy based on observed
behavior: the new flyer has sometimes appeared between Sunday and Monday.
Lidl's publication timing is not known or guaranteed to fall in that window;
the schedule is not a business-logic assumption. The four checks recur each
week, and `workflow_dispatch` remains available for manual runs whenever
needed. This is scheduled polling, not hourly polling or a continuous retry
loop.

Each run discovers the flyers currently advertised by Lidl's API, downloads
any missing PDFs, and extracts product cards using a cache per flyer ID. It
searches those cards for the configured query. It does not infer when a new
flyer should be published or compare against a hard-coded publication window:
whenever Lidl advertises a flyer, a later scheduled or manual run can discover
and search it.

Notifications are deduplicated by `(flyer ID, normalized query)` in
`data/state/watch_state.json`. A pair is recorded after the email attempt, and
the workflow commits the state so subsequent scheduled or manual runs skip
that notification. If there is no match, the run exits normally without
sending an email. Repeated runs are intentional and must remain idempotent:
PDF downloads are reused, extracted cards are cached, and an already-notified
pair is not emailed again. The workflow's final state-commit step does nothing
when the state file is unchanged.

## Local runs

Run the same watcher directly with:

```text
python -m lidl_tracker.cli_watch --query "queso en salmuera" --to <email>
```

`tools/run_watch.bat` is a Windows convenience wrapper that loads local SMTP
settings and logs output; it can be run manually or registered with Windows
Task Scheduler independently of the GitHub Actions schedule.

If SMTP is missing or incomplete, the email is printed as a dry run rather
than sent.

## One-time setup

1. Copy the SMTP config template and fill in real credentials:

   ```
   copy data\config\smtp.env.example data\config\smtp.env
   ```

   For Gmail, `LIDL_SMTP_PASSWORD` must be an App Password (2FA required),
   not the account password.

2. Optionally register a local Windows Task Scheduler task (run once, from an
   elevated or normal prompt). This is separate from the GitHub Actions
   schedule:

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
