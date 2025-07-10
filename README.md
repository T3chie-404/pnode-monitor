# pNode Network Monitor

This application monitors the Xandeum devnet pNode network and sends status updates to a Google Chat webhook at configurable intervals. It tracks:
- Total number of active nodes
- New nodes that have joined the network
- Nodes that have gone offline
- Maintains state between runs to accurately track changes

## Features

- Configurable check interval (default: every 2 hours)
- Sends formatted messages to Google Chat
- Tracks node changes between runs
- Persists state between runs in `pnode_state.json`
- Error handling and logging
- Limits output to show first 5 nodes in each category to avoid message clutter

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
   - Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   - Edit `.env` and add your Google Chat webhook URL:
   ```bash
   vim .env  # or use your preferred editor
   ```
   - The `.env` file should contain:
   ```
   GOOGLE_CHAT_WEBHOOK=your_webhook_url_here
   CHECK_INTERVAL_HOURS=2  # Change this number to adjust check frequency
   ```

   Note: The `.env` file is ignored by Git to keep your webhook URL secure.

## Running the Application

There are two ways to run the application:

### 1. As a Background Service (Recommended)

Run the script in the background with nohup:
```bash
cd /root/pnode_notifier
GOOGLE_CHAT_WEBHOOK='your_webhook_url_here' nohup python pnode_monitor.py > pnode_monitor.log 2>&1 &
```

This will:
- Run the script in the background
- Continue running after terminal closes
- Log output to `pnode_monitor.log`

To stop the service:
```bash
pkill -f pnode_monitor.py
```

To check the logs:
```bash
tail -f pnode_monitor.log
```

### 2. In the Terminal

For testing or debugging, run directly:
```bash
python pnode_monitor.py
```

## What the Application Does

1. Initial Run:
   - Performs immediate check of active nodes
   - Establishes baseline for future comparisons
   - Sends initial status report

2. Subsequent Runs (every 6 hours):
   - Checks for new nodes that joined
   - Identifies nodes that went offline
   - Sends detailed status report
   - Updates state file

## Sample Output

```
🚀 Initial pNode Network Status - 2024-01-01 12:00:00

• Total Active Nodes: 23

📊 Later Status Update - 2024-01-01 18:00:00

• Total Active Nodes: 31

🆕 New Nodes (10) 🆕
• node1.example.com:5000
• node2.example.com:5000
• node3.example.com:5000
• node4.example.com:5000
• node5.example.com:5000
• ... and 5 more

⚠️ Offline Nodes (2) ⚠️
• offline1.example.com:5000
• offline2.example.com:5000
```

## Error Handling

The application handles various error cases:
- Network connectivity issues
- API response errors
- Webhook delivery failures
- State file read/write errors

Errors are logged to `pnode_monitor.log`

## State Persistence

The application maintains state in `pnode_state.json` to:
- Track node changes between runs
- Survive process restarts
- Provide accurate change detection

## Note

While the background service will continue running if you close your terminal, it will not automatically restart after system reboots. If you need that functionality, consider setting up a proper systemd service. 