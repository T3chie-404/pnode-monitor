# AI Bot Development Log - pNode Network Monitor

## Project Overview
This project is a Python-based monitoring system for the Xandeum devnet pNode network. It tracks node status changes and reports them via Google Chat webhooks.

## Repository Information
- **Repository**: github.com/T3chie-404/pnode-monitor
- **Created**: July 2023
- **Initial Setup**: Used SSH key (/root/.ssh/id_ed25519_t3chie) for repository creation
- **Environment**: Linux server (Hulk) running Python

## Core Components
1. **Main Script**: `pnode_monitor.py`
   - Monitors Xandeum devnet pNode network
   - Endpoint: atlas.devnet.xandeum.com:3000/api/pods
   - Uses webhook for notifications
   - Implements state persistence
   - Background service architecture

2. **Configuration**:
   - Uses `.env` for environment variables
   - Webhook URL stored securely (not in repo)
   - Configurable check interval (default: 2 hours)

3. **Dependencies** (`requirements.txt`):
   - requests: HTTP client for API calls
   - python-dateutil: Date handling
   - schedule: Task scheduling
   - python-dotenv: Environment variable management

## Development Timeline

### Initial Implementation (July 2023)
1. **Basic Monitoring Setup**
   - Created basic HTTP client for pNode API
   - Implemented webhook notifications
   - Set up initial state tracking
   - First deployment showed 23 active nodes

### Major Enhancement: Robust Error Handling (July 2023)
1. **API Reliability Improvements**
   - Added retry mechanism (3 attempts, 5-second delays)
   - Implemented majority-based node verification
   - Enhanced error logging
   - Added timeout handling

2. **State Management**
   - Added JSON-based state persistence
   - Implemented state file backup system
   - Added state validation checks

### Critical Update: False Positive Prevention (July 2023)
1. **Node Change Validation**
   - Added thresholds for acceptable changes (50% max)
   - Implemented change validation logic
   - Added skipped update notifications
   - Enhanced logging for state operations

2. **Message Formatting**
   - Differentiated message types (initial, update, skipped)
   - Limited node list display (5 nodes + count)
   - Added timestamps and emojis for better readability

### Feature Enhancement: Critical Alert System (August 2025)
1. **Zero-Node Alerting**
   - Implemented a special alert for when the API reports zero nodes after previously reporting a non-zero count.
   - This prevents the state from being incorrectly updated to zero nodes.
   - The alert repeats on each check until the API recovers, ensuring the issue is not missed.

2. **Timestamped Logging**
   - Added a dedicated logging function to prepend a timestamp to all console output.
   - Replaced all `print()` calls with the new logging function for improved traceability.
   - Recommended running the background service with Python's unbuffered (`-u`) flag to ensure logs are written immediately.

## Technical Decisions and Rationales

### State Management Design
1. **Why JSON for State Storage**:
   - Human-readable format
   - Easy to debug and modify
   - Native Python dictionary conversion
   - Lightweight and sufficient for needs

2. **Backup System**:
   - Creates backup before state updates
   - Prevents data loss during crashes
   - Allows state recovery if needed

### Node Validation System
1. **Multiple API Calls**:
   - Prevents false readings from temporary network issues
   - Uses majority consensus for node status
   - Reduces false positives/negatives

2. **Change Thresholds**:
   - 50% maximum change limit
   - Based on observation of normal network behavior
   - Prevents mass false reports during API issues

### Background Service Architecture
1. **Using nohup**:
   - Ensures process continues after terminal closes
   - Redirects output to log file
   - Simple but effective for single-server deployment
   - **Update**: Recommended using `python -u` to disable output buffering for real-time logs.

2. **Log File Strategy**:
   - Separate log file for debugging
   - Captures all stdout/stderr
   - Aids in troubleshooting
   - **Update**: Logs are now timestamped for clarity.

## Known Limitations and Future Improvements
1. **Current Limitations**:
   - Single-server deployment
   - Basic retry mechanism
   - Limited historical data analysis

2. **Potential Improvements**:
   - Add database for historical tracking
   - Implement node uptime statistics
   - Add alert severity levels
   - Create web dashboard
   - Add unit tests

## Deployment Notes
- Running on Hulk server
- Uses tmux for process management
- Logs stored in `pnode_monitor.log`
- State stored in `pnode_state.json`

## Security Considerations
1. **API Security**:
   - No authentication required for pNode API
   - Uses HTTPS for webhook communication
   - Timeouts prevent hanging connections

2. **Configuration Security**:
   - Webhook URL in .env file
   - No sensitive data in repository
   - State file contains no sensitive information

## Troubleshooting Guide
1. **Common Issues**:
   - False offline reports: Check API connectivity
   - Missing updates: Verify webhook URL
   - State reset: Check file permissions
   - **Log file is empty**: Ensure you are running the service with `python -u`.

2. **Debug Steps**:
   - Check pnode_monitor.log for timestamped errors.
   - Verify state file contents
   - Confirm webhook URL in .env
   - Check process status with ps/top

## Change Management Protocol
For AI assistants maintaining this project:
1. Always validate state file before/after changes
2. Maintain retry mechanism in API calls
3. Keep change thresholds unless explicitly requested
4. Update this log with significant changes
5. Document rationale for threshold adjustments
6. Preserve error handling mechanisms
7. Maintain backup system for state files

---
*This log is maintained by AI assistants to track project evolution and decision rationale. It should be updated with each significant change or decision.*
