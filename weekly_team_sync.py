import subprocess
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request
import threading
import webbrowser
import socket
from contextlib import closing
import os

def get_github_token():
    """Extract GitHub token from gh auth token command"""
    try:
        result = subprocess.run(['gh', 'auth', 'token'], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error getting GitHub token: {e}")
        return None

def find_free_port():
    """Find a free port to run the Flask server"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def collect_weekly_responses(qotw=None):
    """Collect responses to weekly questions using a web interface"""
    questions = [
        "How have you been this week?",
        "Your response to the question of the week (QOTW)",
        "Do you have any accounts at risk?",
        "What challenges are you working on?",
        "What did you learn this week that others should know? Is it worth reduxing?",
        "What have you explored or tried this week with AI? Have you learned something new or implemented an idea?",
        "Anything else that's on your mind?",
        "Any upcoming time off?",
        "Have you scheduled any L&D?"
    ]
    
    app = Flask(__name__, template_folder=os.path.dirname(os.path.abspath(__file__)))
    responses = {}
    server_running = threading.Event()
    
    @app.route('/', methods=['GET', 'POST'])
    def index():
        if request.method == 'POST':
            # Collect responses from form
            for i, question in enumerate(questions):
                response = request.form.get(f'question_{i}', '').strip()
                responses[question] = response
            
            # Check if any responses have actual content
            has_responses = any(response.strip() for response in responses.values())
            
            if has_responses:
                server_running.set()
                return render_template('template.html', questions=questions, qotw=qotw, success=True, empty_submission=False)
            else:
                # Show error for empty submission
                return render_template('template.html', questions=questions, qotw=qotw, success=False, empty_submission=True)
        
        return render_template('template.html', questions=questions, qotw=qotw, success=False, empty_submission=False)
    
    @app.route('/shutdown', methods=['GET', 'POST'])
    def shutdown():
        """Allow manual shutdown when browser is closed"""
        print("\nBrowser closed. Shutting down...")
        server_running.set()
        return 'Shutting down...'
    
    @app.before_request
    def check_shutdown():
        """Check if we should shutdown on connection issues"""
        pass
    
    port = find_free_port()
    
    def run_server():
        try:
            app.run(port=port, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            print(f"Server error: {e}")
            server_running.set()
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    url = f"http://localhost:{port}"
    print(f"Opening web interface at {url}")
    print("(Close browser tab or press Ctrl+C to exit)")
    webbrowser.open(url)
    
    try:
        # Wait for responses with a timeout to allow checking for shutdown
        while not server_running.wait(timeout=1.0):
            # Check if server thread is still alive
            if not server_thread.is_alive():
                print("\nServer stopped. Exiting...")
                break
    except KeyboardInterrupt:
        print("\nShutting down...")
        server_running.set()
    
    return responses

def format_comment(responses):
    """Format responses as markdown comment"""
    comment_body = ""
    for question, answer in responses.items():
        comment_body += f"**{question}**\n{answer}\n\n"
    return comment_body.strip()

def post_comment_to_issue(token, issue_number, comment_body):
    """Post a comment to a GitHub issue"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # You'll need to update this URL with your actual repo
    url = f"https://api.github.com/repos/github/premium-support/issues/{issue_number}/comments"
    
    data = {
        "body": comment_body
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        comment = response.json()
        print(f"Comment posted successfully! Comment ID: {comment['id']}")
        print(f"Comment URL: {comment['html_url']}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error posting comment: {e}")
        return False

def fetch_weekly_issue(token):
    """Fetch open issues from GitHub repository updated in last week with team-meeting label"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Calculate date one week ago
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    params = {
        "state": "open",
        "since": one_week_ago,
        "labels": "team-meeting"
    }
    
    url = "https://api.github.com/repos/github/premium-support/issues"
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        issues = response.json()
        
        if len(issues) == 0:
            print("No open issues found with 'team-meeting' label")
            return None, None
        elif len(issues) == 1:
            issue = issues[0]
            print(f"Found issue #{issue['number']}: {issue['title']}")
            
            # Parse QOTW from issue body
            qotw = None
            body = issue.get('body', '')
            
            if body:
                lines = body.split('\n')
                for line_num, line in enumerate(lines):
                    line = line.strip()
                    if line.startswith('> QOTW:'):
                        # Extract QOTW text, removing the "> QOTW: " prefix and any quotes
                        qotw = line[7:].strip().strip('"').strip("'")
                        print(f"Found QOTW (format 1): {qotw}")
                        break
                    elif line.startswith('QOTW:'):
                        # Extract QOTW text, removing the "QOTW: " prefix and any quotes
                        qotw = line[5:].strip().strip('"').strip("'")
                        print(f"Found QOTW (format 2): {qotw}")
                        break
            
            if not qotw:
                print("No QOTW found in issue body")
            
            return issue['number'], qotw
        else:
            issue_ids = [issue['number'] for issue in issues]
            raise ValueError(f"Expected exactly one issue, but found {len(issues)}: {issue_ids}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching issues: {e}")
        return None, None


if __name__ == "__main__":
    token = get_github_token()
    if token:
        issue_number, qotw = fetch_weekly_issue(token)
        if issue_number:
            if qotw:
                print(f"QOTW: {qotw}")
            
            # Collect weekly responses from user using web interface
            responses = collect_weekly_responses(qotw)
            
            # Check if user actually submitted (not just closed the window)
            if any(response.strip() for response in responses.values()):
                # Format responses as markdown comment
                comment_body = format_comment(responses)
                
                # Post comment to the issue
                success = post_comment_to_issue(token, issue_number, comment_body)
                
                if success:
                    print("✅ Weekly sync responses submitted successfully!")
                else:
                    print("❌ Failed to submit weekly sync responses.")
            else:
                print("No responses provided. Exiting without submitting.")
        else:
            print("❌ No weekly issue found to comment on.")
    else:
        print("❌ Failed to retrieve GitHub token.")