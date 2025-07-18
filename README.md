# CalMac Ferry Availability Checker

An automated Python script that checks CalMac ferry availability hourly using GitHub Actions and sends Telegram notifications when your target route becomes available.

## 🎯 What it does

- **Automates ferry booking flow** using Playwright to check availability
- **Runs hourly** via GitHub Actions
- **Sends Telegram alerts** when ferries become available
- **Logs all activity** for debugging and monitoring

## 📋 Target Route

- **Outbound**: Troon → Brodick on Sunday, 3 August @ 07:45
- **Return**: Brodick → Troon on Tuesday, 5 August @ 15:30
- **Passengers**: 1 Adult, 1 Child, 1 Infant
- **Vehicle**: Car (Tesla Model Y)

## 🚀 Setup Instructions

### 1. Repository Setup

1. Fork or clone this repository
2. The required files are already included:
   ```
   /calmac-checker
   ├── check_availability.py      # Main automation script
   ├── requirements.txt           # Python dependencies
   ├── .github/workflows/
   │   └── check_ferry.yml       # GitHub Actions workflow
   └── README.md                 # This file
   ```

### 2. Telegram Bot Setup

1. **Create a Telegram Bot**:
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` and follow instructions
   - Save your `Bot Token`

2. **Get your Chat ID**:
   - Message your new bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find your `chat.id` in the response

### 3. GitHub Secrets Configuration

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these two secrets:

| Secret Name | Value |
|-------------|-------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Your chat ID from the API call |

### 4. Enable GitHub Actions

1. Go to the **Actions** tab in your repository
2. Enable workflows if prompted
3. The script will run automatically every hour

## 🔧 Manual Testing

You can trigger the workflow manually:

1. Go to **Actions** tab
2. Select "CalMac Ferry Availability Checker"
3. Click "Run workflow"

## 📊 Monitoring

- **View logs**: Check the Actions tab for detailed run logs
- **Download artifacts**: Logs are saved as artifacts for 7 days
- **Telegram notifications**: You'll receive messages only when availability is found

## 🛠️ Local Development

To test locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Set environment variables
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# Run the script
python check_availability.py
```

## 📝 Expected Telegram Message

When availability is found, you'll receive:

```
🚢 CalMac Alert! Your ferry is now available:

Outbound: Troon → Brodick on Sun 03 Aug @ 07:45  
Return: Brodick → Troon on Tue 05 Aug @ 15:30  

Book now: https://ticketing.calmac.co.uk/B2C-Calmac/

Checked at: 2025-07-18 14:30:00 UTC
```

## 🔍 Troubleshooting

### Common Issues

1. **No Telegram messages**: Check your bot token and chat ID in GitHub secrets
2. **Workflow not running**: Ensure the workflow file is in `.github/workflows/`
3. **Script errors**: Check the Actions logs for detailed error messages

### Debug Features

- **Screenshots**: Error screenshots are saved to logs when issues occur
- **Detailed logging**: All steps are logged with timestamps
- **Artifact uploads**: Logs are preserved for 7 days

## ⚡ Customization

### Change Target Route

Edit the dates and route in `check_availability.py`:

```python
# Set outbound date
await outbound_date_input.fill('03/08/2025')

# Set return date  
await return_date_input.fill('05/08/2025')
```

### Change Check Frequency

Edit the cron schedule in `.github/workflows/check_ferry.yml`:

```yaml
schedule:
  # Every 30 minutes: '*/30 * * * *'
  # Every 2 hours: '0 */2 * * *'
  - cron: '0 * * * *'  # Current: every hour
```

## 📜 License

This project is open source and available under the [MIT License](LICENSE).

## ⚠️ Disclaimer

This tool is for personal use only. Please respect CalMac's terms of service and don't overload their servers with excessive requests.
