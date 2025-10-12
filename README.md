# Teshima Art Museum Slot Watcher

A GitHub Action that monitors ticket availability for the Teshima Art Museum and sends email notifications when slots become available.

## Features

- Monitors the [Teshima Art Museum booking page](https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/185773) every 10 minutes
- Checks availability for specific dates (October 20-24, 2024)
- Sends email notifications via SendGrid when tickets become available
- Tracks state between runs to avoid duplicate notifications

## Setup

1. **Fork this repository** to your GitHub account

2. **Set up SendGrid**:
   - Create a SendGrid account at [sendgrid.com](https://sendgrid.com)
   - Generate an API key
   - Add it as a repository secret named `SENDGRID_API_KEY`

3. **Configure email**:
   - Add your email address as a repository secret named `TARGET_EMAIL`
   - Or modify the default email in the code

4. **Enable GitHub Actions**:
   - Go to your repository's Actions tab
   - Enable GitHub Actions if not already enabled
   - The workflow will run automatically every 10 minutes

## How it works

The GitHub Action:
1. Runs every 10 minutes via cron schedule
2. Fetches the booking page
3. Parses the calendar to detect availability symbols:
   - ⭕ Circle = Available for purchase
   - 🔺 Triangle = Only a few left  
   - ❌ Cross = Sold out
   - "Closed" = Not available
4. Compares with previous state to detect changes
5. Sends email notification if any target date becomes available
6. Saves current state for next run

## Manual Testing

You can manually trigger the workflow:
1. Go to Actions tab in your repository
2. Select "Teshima Art Museum Slot Watcher"
3. Click "Run workflow"

## Monitoring

Check the Actions tab to see:
- When the workflow last ran
- Success/failure status
- Logs from each run

## Customization

You can modify:
- Target dates in `slot_watcher.py`
- Check interval in `.github/workflows/slot-watcher.yml`
- Email template in the notification function
- Monitoring URL if needed

## Troubleshooting

- Check the Actions logs for error messages
- Ensure SendGrid API key is valid
- Verify the target email is correct
- Check if the booking page structure has changed
