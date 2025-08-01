import requests
import json
import time
import schedule
from datetime import datetime
import os
from typing import Set, Dict, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def log_message(message: str):
    """Prints a message with a timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

class PNodeMonitor:
    def __init__(self, webhook_url: str, check_interval_hours: int):
        self.api_url = "http://atlas.devnet.xandeum.com:3000/api/pods"
        self.webhook_url = webhook_url
        self.check_interval_hours = check_interval_hours
        self.previous_nodes: Set[str] = set()
        self.first_run = True
        
        # Load previous state if exists
        self.state_file = "pnode_state.json"
        self.load_state()

    def load_state(self):
        """Load the previous state from file if it exists."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    loaded_nodes = set(data.get('nodes', []))
                    # Sanity check: only accept state if it's not empty
                    if loaded_nodes:
                        log_message(f"Loaded previous state with {len(loaded_nodes)} nodes")
                        self.previous_nodes = loaded_nodes
                        self.first_run = False
                    else:
                        log_message("Previous state was empty, treating as first run")
            else:
                log_message("No previous state found, treating as first run")
        except Exception as e:
            log_message(f"Error loading state: {e}")

    def save_state(self, nodes: Set[str]):
        """Save the current state to file."""
        try:
            # Only save state if we have nodes
            if nodes:
                # Create a backup of the current state file if it exists
                if os.path.exists(self.state_file):
                    backup_file = f"{self.state_file}.backup"
                    try:
                        with open(self.state_file, 'r') as src, open(backup_file, 'w') as dst:
                            dst.write(src.read())
                    except Exception as e:
                        log_message(f"Error creating backup: {e}")

                with open(self.state_file, 'w') as f:
                    json.dump({'nodes': list(nodes)}, f)
                log_message(f"Saved state with {len(nodes)} nodes")
            else:
                log_message("No nodes to save, skipping state save")
        except Exception as e:
            log_message(f"Error saving state: {e}")

    def get_nodes_with_retry(self, retries: int = 3, delay: int = 5) -> Set[str]:
        """Fetch current nodes from the API with retries and verification."""
        all_results = []
        
        # Make multiple API calls
        for attempt in range(retries):
            try:
                response = requests.get(self.api_url, timeout=10)
                response.raise_for_status()
                # Handle cases where 'pods' key might be missing
                nodes = set(response.json().get('pods', []))
                all_results.append(nodes)
                log_message(f"API call {attempt + 1}: Found {len(nodes)} nodes")
                
                if attempt < retries - 1:  # Don't sleep on the last attempt
                    time.sleep(delay)
                    
            except requests.exceptions.RequestException as e:
                log_message(f"Error in API call {attempt + 1}: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
                continue
            except json.JSONDecodeError as e:
                log_message(f"Error decoding JSON in API call {attempt + 1}: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
                continue

        if not all_results:
            log_message("All API calls failed to return data.")
            return set()

        # If all results are empty, return an empty set
        if all(not res for res in all_results):
            log_message("All API calls resulted in zero nodes.")
            return set()

        # Find nodes that appear in the majority of results
        if len(all_results) == 1:
            return all_results[0]
        
        node_sets = list(all_results)
        
        consistent_nodes = set()
        all_seen_nodes = set().union(*node_sets)
        
        for node in all_seen_nodes:
            appearances = sum(1 for node_set in node_sets if node in node_set)
            if appearances >= len(node_sets) // 2 + 1:
                consistent_nodes.add(node)
        
        log_message(f"Found {len(consistent_nodes)} consistent nodes across {len(all_results)} API calls")
        return consistent_nodes

    def validate_changes(self, current_nodes: Set[str], new_nodes: Set[str], offline_nodes: Set[str]) -> bool:
        """Validate that the changes make sense."""
        if self.first_run:
            return True

        total_previous = len(self.previous_nodes)
        if total_previous == 0:
            return True

        new_percentage = (len(new_nodes) / total_previous) * 100 if total_previous > 0 else 0
        offline_percentage = (len(offline_nodes) / total_previous) * 100 if total_previous > 0 else 0

        MAX_NEW_PERCENTAGE = 50
        MAX_OFFLINE_PERCENTAGE = 50

        if new_percentage > MAX_NEW_PERCENTAGE:
            log_message(f"Warning: Suspicious number of new nodes ({new_percentage:.1f}% increase)")
            return False

        if offline_percentage > MAX_OFFLINE_PERCENTAGE:
            log_message(f"Warning: Suspicious number of offline nodes ({offline_percentage:.1f}% decrease)")
            return False

        return True

    def analyze_changes(self, current_nodes: Set[str]) -> Dict:
        """Analyze changes between current and previous node sets."""
        if not current_nodes and self.previous_nodes:
            log_message("CRITICAL: Node count dropped to zero from a non-zero state.")
            return {
                'total_nodes': 0,
                'previous_total_nodes': len(self.previous_nodes),
                'new_nodes': [],
                'offline_nodes': list(self.previous_nodes),
                'is_first_run': False,
                'skipped_update': False,
                'api_error_drop_to_zero': True
            }

        if self.first_run:
            self.first_run = False
            return {
                'total_nodes': len(current_nodes),
                'new_nodes': list(current_nodes),
                'offline_nodes': [],
                'is_first_run': True
            }

        new_nodes = current_nodes - self.previous_nodes
        offline_nodes = self.previous_nodes - current_nodes

        if not self.validate_changes(current_nodes, new_nodes, offline_nodes):
            log_message("Changes failed validation, using previous state")
            return {
                'total_nodes': len(self.previous_nodes),
                'new_nodes': [],
                'offline_nodes': [],
                'is_first_run': False,
                'skipped_update': True
            }

        return {
            'total_nodes': len(current_nodes),
            'new_nodes': list(new_nodes),
            'offline_nodes': list(offline_nodes),
            'is_first_run': False,
            'skipped_update': False
        }

    def format_message(self, stats: Dict) -> str:
        """Format the statistics into a readable message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if stats.get('api_error_drop_to_zero'):
            message = f"🚨 *CRITICAL ALERT: pNode API Failure* - {timestamp}\n\n"
            message += "• The API is reporting ZERO active nodes.\n"
            message += f"• Previously, there were {stats['previous_total_nodes']} nodes.\n"
            message += "• This could indicate a major network outage or API failure.\n"
            message += "• *Action required: Please investigate immediately.*\n"
            return message

        if stats['is_first_run']:
            message = f"🚀 *Initial pNode Network Status* - {timestamp}\n\n"
            message += f"• Total Active Nodes: {stats['total_nodes']}\n"
            return message

        if stats.get('skipped_update', False):
            message = f"⚠️ *pNode Network Status Update (Skipped)* - {timestamp}\n\n"
            message += "• Update skipped due to suspicious changes (e.g., >50% change).\n"
            message += f"• Maintaining previous count: {stats['total_nodes']} nodes\n"
            return message

        message = f"📊 *pNode Network Status Update* - {timestamp}\n\n"
        message += f"• Total Active Nodes: {stats['total_nodes']}\n"
        
        if stats['new_nodes']:
            message += f"\n🆕 *New Nodes ({len(stats['new_nodes'])})* 🆕\n"
            for node in sorted(stats['new_nodes'])[:5]:
                message += f"• {node}\n"
            if len(stats['new_nodes']) > 5:
                message += f"• ... and {len(stats['new_nodes']) - 5} more\n"

        if stats['offline_nodes']:
            message += f"\n⚠️ *Offline Nodes ({len(stats['offline_nodes'])})* ⚠️\n"
            for node in sorted(stats['offline_nodes'])[:5]:
                message += f"• {node}\n"
            if len(stats['offline_nodes']) > 5:
                message += f"• ... and {len(stats['offline_nodes']) - 5} more\n"

        return message

    def send_to_webhook(self, message: str):
        """Send the formatted message to Google Chat webhook."""
        try:
            payload = {'text': message}
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            log_message("Message sent successfully")
        except requests.exceptions.RequestException as e:
            log_message(f"Error sending message: {e}")

    def run_check(self):
        """Run a single check of the network status."""
        current_nodes = self.get_nodes_with_retry()
        
        stats = self.analyze_changes(current_nodes)
        message = self.format_message(stats)
        self.send_to_webhook(message)
        
        if stats.get('api_error_drop_to_zero'):
            log_message("State not saved to ensure critical alert repeats if issue persists.")
            return

        if not stats.get('skipped_update'):
            self.previous_nodes = current_nodes
            self.save_state(current_nodes)

def main():
    webhook_url = os.getenv('GOOGLE_CHAT_WEBHOOK')
    if not webhook_url:
        log_message("Error: GOOGLE_CHAT_WEBHOOK environment variable not set")
        return

    try:
        check_interval = int(os.getenv('CHECK_INTERVAL_HOURS', '2'))
        if check_interval < 1:
            log_message("Warning: CHECK_INTERVAL_HOURS must be at least 1, using default of 2")
            check_interval = 2
    except ValueError:
        log_message("Warning: Invalid CHECK_INTERVAL_HOURS value, using default of 2")
        check_interval = 2

    monitor = PNodeMonitor(webhook_url, check_interval)
    
    log_message(f"Starting pNode monitor with {check_interval} hour check interval")
    
    schedule.every(check_interval).hours.do(monitor.run_check)
    
    monitor.run_check()
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
