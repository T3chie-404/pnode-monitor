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
                    self.previous_nodes = set(data['nodes'])
                    self.first_run = False
        except Exception as e:
            print(f"Error loading state: {e}")

    def save_state(self, nodes: Set[str]):
        """Save the current state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump({'nodes': list(nodes)}, f)
        except Exception as e:
            print(f"Error saving state: {e}")

    def get_nodes_with_retry(self, retries: int = 3, delay: int = 5) -> Set[str]:
        """Fetch current nodes from the API with retries and verification."""
        all_results = []
        
        # Make multiple API calls
        for attempt in range(retries):
            try:
                response = requests.get(self.api_url, timeout=10)
                response.raise_for_status()
                nodes = set(response.json()['pods'])
                all_results.append(nodes)
                print(f"API call {attempt + 1}: Found {len(nodes)} nodes")
                
                if attempt < retries - 1:  # Don't sleep on the last attempt
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"Error in API call {attempt + 1}: {e}")
                if attempt < retries - 1:  # Don't sleep on the last attempt
                    time.sleep(delay)
                continue
        
        if not all_results:
            print("All API calls failed")
            return set()
        
        # Find nodes that appear in the majority of results
        if len(all_results) == 1:
            return all_results[0]
        
        # Convert all sets to a list of sets for intersection
        node_sets = list(all_results)
        
        # Find nodes that appear in at least 2 results
        consistent_nodes = set()
        all_seen_nodes = set().union(*node_sets)
        
        for node in all_seen_nodes:
            appearances = sum(1 for node_set in node_sets if node in node_set)
            if appearances >= len(node_sets) // 2 + 1:  # Majority of results
                consistent_nodes.add(node)
        
        print(f"Found {len(consistent_nodes)} consistent nodes across {len(all_results)} API calls")
        return consistent_nodes

    def analyze_changes(self, current_nodes: Set[str]) -> Dict:
        """Analyze changes between current and previous node sets."""
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

        return {
            'total_nodes': len(current_nodes),
            'new_nodes': list(new_nodes),
            'offline_nodes': list(offline_nodes),
            'is_first_run': False
        }

    def format_message(self, stats: Dict) -> str:
        """Format the statistics into a readable message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if stats['is_first_run']:
            message = f"🚀 *Initial pNode Network Status* - {timestamp}\n\n"
            message += f"• Total Active Nodes: {stats['total_nodes']}\n"
            return message

        message = f"📊 *pNode Network Status Update* - {timestamp}\n\n"
        message += f"• Total Active Nodes: {stats['total_nodes']}\n"
        
        if stats['new_nodes']:
            message += f"\n🆕 *New Nodes ({len(stats['new_nodes'])})* 🆕\n"
            for node in sorted(stats['new_nodes'])[:5]:  # Show first 5 new nodes
                message += f"• {node}\n"
            if len(stats['new_nodes']) > 5:
                message += f"• ... and {len(stats['new_nodes']) - 5} more\n"

        if stats['offline_nodes']:
            message += f"\n⚠️ *Offline Nodes ({len(stats['offline_nodes'])})* ⚠️\n"
            for node in sorted(stats['offline_nodes'])[:5]:  # Show first 5 offline nodes
                message += f"• {node}\n"
            if len(stats['offline_nodes']) > 5:
                message += f"• ... and {len(stats['offline_nodes']) - 5} more\n"

        return message

    def send_to_webhook(self, message: str):
        """Send the formatted message to Google Chat webhook."""
        try:
            payload = {'text': message}
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            print("Message sent successfully")
        except Exception as e:
            print(f"Error sending message: {e}")

    def run_check(self):
        """Run a single check of the network status."""
        current_nodes = self.get_nodes_with_retry()
        if not current_nodes:
            print("No valid node data obtained, skipping update")
            return

        stats = self.analyze_changes(current_nodes)
        message = self.format_message(stats)
        self.send_to_webhook(message)
        
        # Update previous nodes and save state
        self.previous_nodes = current_nodes
        self.save_state(current_nodes)

def main():
    # Get configuration from environment variables
    webhook_url = os.getenv('GOOGLE_CHAT_WEBHOOK')
    if not webhook_url:
        print("Error: GOOGLE_CHAT_WEBHOOK environment variable not set")
        return

    # Get check interval from environment variable (default to 2 hours)
    try:
        check_interval = int(os.getenv('CHECK_INTERVAL_HOURS', '2'))
        if check_interval < 1:
            print("Warning: CHECK_INTERVAL_HOURS must be at least 1, using default of 2")
            check_interval = 2
    except ValueError:
        print("Warning: Invalid CHECK_INTERVAL_HOURS value, using default of 2")
        check_interval = 2

    monitor = PNodeMonitor(webhook_url, check_interval)
    
    print(f"Starting pNode monitor with {check_interval} hour check interval")
    
    # Schedule runs based on configured interval
    schedule.every(check_interval).hours.do(monitor.run_check)
    
    # Run initial check
    monitor.run_check()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main() 