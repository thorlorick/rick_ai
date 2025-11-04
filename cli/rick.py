#!/usr/bin/env python3
"""
Rick AI - Terminal Client
A beautiful CLI for your AI coding assistant
"""
import requests
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner

# Configuration
API_URL = "http://127.0.0.1:8090"
CONFIG_DIR = Path.home() / ".rick"
CONVERSATIONS_DIR = CONFIG_DIR / "conversations"
PROJECTS_DIR = CONFIG_DIR / "projects"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Initialize directories
CONFIG_DIR.mkdir(exist_ok=True)
CONVERSATIONS_DIR.mkdir(exist_ok=True)
PROJECTS_DIR.mkdir(exist_ok=True)

console = Console()

class RickCLI:
    def __init__(self):
        self.messages = []
        self.current_conversation_id = None
        self.current_project = None
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {
            "last_conversation": None,
            "current_project": None,
            "theme": "dark"
        }
    
    def save_config(self):
        """Save configuration"""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def save_conversation(self, title=None):
        """Save current conversation"""
        if not self.messages:
            console.print("[yellow]No messages to save[/yellow]")
            return
        
        if not title:
            # Auto-generate title from first user message
            first_msg = next((m for m in self.messages if m['role'] == 'user'), None)
            if first_msg:
                title = first_msg['content'][:50]
            else:
                title = "Untitled"
        
        conv_id = f"conv_{datetime.now().timestamp()}"
        
        conversation = {
            "id": conv_id,
            "title": title,
            "messages": self.messages,
            "created_at": datetime.now().isoformat(),
            "project": self.current_project
        }
        
        # Save to appropriate directory
        if self.current_project:
            project_dir = PROJECTS_DIR / self.current_project / "conversations"
            project_dir.mkdir(parents=True, exist_ok=True)
            filepath = project_dir / f"{conv_id}.json"
        else:
            filepath = CONVERSATIONS_DIR / f"{conv_id}.json"
        
        with open(filepath, 'w') as f:
            json.dump(conversation, f, indent=2)
        
        console.print(f"[green]✓ Saved as:[/green] {title}")
        return conv_id
    
    def load_conversation(self, conv_id):
        """Load a conversation by ID"""
        # Search in current project first, then global
        search_paths = []
        if self.current_project:
            search_paths.append(PROJECTS_DIR / self.current_project / "conversations")
        search_paths.append(CONVERSATIONS_DIR)
        
        for path in search_paths:
            filepath = path / f"{conv_id}.json"
            if filepath.exists():
                with open(filepath, 'r') as f:
                    conversation = json.load(f)
                    self.messages = conversation['messages']
                    self.current_conversation_id = conv_id
                    console.print(f"[green]✓ Loaded:[/green] {conversation['title']}")
                    self.display_history()
                    return
        
        console.print(f"[red]✗ Conversation not found:[/red] {conv_id}")
    
    def list_conversations(self):
        """List all conversations"""
        conversations = []
        
        # Get conversations from current project
        if self.current_project:
            project_conv_dir = PROJECTS_DIR / self.current_project / "conversations"
            if project_conv_dir.exists():
                for file in project_conv_dir.glob("*.json"):
                    with open(file, 'r') as f:
                        conv = json.load(f)
                        conversations.append(conv)
        else:
            # Get all global conversations
            for file in CONVERSATIONS_DIR.glob("*.json"):
                with open(file, 'r') as f:
                    conv = json.load(f)
                    if not conv.get('project'):  # Only unorganized
                        conversations.append(conv)
        
        if not conversations:
            console.print("[yellow]No conversations found[/yellow]")
            return
        
        # Sort by date
        conversations.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        console.print("\n[bold cyan]Conversations:[/bold cyan]")
        for i, conv in enumerate(conversations[:20], 1):
            created = datetime.fromisoformat(conv['created_at']).strftime("%Y-%m-%d %H:%M")
            console.print(f"  {i}. [dim]{conv['id']}[/dim] - {conv['title'][:60]} [dim]({created})[/dim]")
        
        console.print(f"\n[dim]Use /load <id> to load a conversation[/dim]")
    
    def create_project(self, name):
        """Create or switch to a project"""
        project_dir = PROJECTS_DIR / name
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "conversations").mkdir(exist_ok=True)
        
        self.current_project = name
        self.config['current_project'] = name
        self.save_config()
        
        console.print(f"[green]✓ Switched to project:[/green] {name}")
    
    def list_projects(self):
        """List all projects"""
        projects = [p.name for p in PROJECTS_DIR.iterdir() if p.is_dir()]
        
        if not projects:
            console.print("[yellow]No projects yet[/yellow]")
            console.print("[dim]Use /project <name> to create one[/dim]")
            return
        
        console.print("\n[bold cyan]Projects:[/bold cyan]")
        for project in sorted(projects):
            marker = "→" if project == self.current_project else " "
            conv_count = len(list((PROJECTS_DIR / project / "conversations").glob("*.json")))
            console.print(f"  {marker} {project} [dim]({conv_count} conversations)[/dim]")
    
    def display_history(self):
        """Display conversation history"""
        console.print("\n[bold cyan]Conversation History:[/bold cyan]")
        for msg in self.messages:
            role = msg['role'].capitalize()
            color = "green" if msg['role'] == 'user' else "blue"
            
            console.print(f"\n[{color}]{role}:[/{color}]")
            
            # Render markdown for assistant messages
            if msg['role'] == 'assistant':
                md = Markdown(msg['content'])
                console.print(md)
            else:
                console.print(msg['content'])
    
    def send_message(self, message):
        """Send message to Rick and stream response"""
        # Add user message
        self.messages.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Prepare request
        payload = {
            "message": message,
            "conversation_history": self.messages[-6:],  # Last 6 messages
            "max_tokens": 2048,
            "temperature": 0.7
        }
        
        try:
            console.print("\n[blue]Rick:[/blue] ", end='')
            
            response_text = ""
            done = False
            
            # Stream response
            with requests.post(
                f"{API_URL}/chat",
                json=payload,
                stream=True,
                timeout=120
            ) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        
                        # Skip empty lines
                        if not line.strip():
                            continue
                        
                        # Parse SSE format
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                
                                if data['type'] == 'token':
                                    token = data['content']
                                    response_text += token
                                    console.print(token, end='', style="")
                                
                                elif data['type'] == 'status':
                                    # Optionally show status messages
                                    # console.print(f"[dim]{data['content']}[/dim]", end=' ')
                                    pass
                                
                                elif data['type'] == 'done':
                                    done = True
                                    break
                                
                                elif data['type'] == 'error':
                                    console.print(f"\n[red]Error: {data.get('message', 'Unknown error')}[/red]")
                                    return
                            
                            except json.JSONDecodeError as e:
                                # Skip malformed JSON
                                console.print(f"\n[yellow]Warning: Skipped malformed data[/yellow]")
                                continue
                            except KeyError as e:
                                # Missing expected field
                                console.print(f"\n[yellow]Warning: Unexpected data format: {e}[/yellow]")
                                continue
            
            console.print()  # New line after response
            
            # Only add message if we got content
            if response_text.strip():
                self.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                console.print("[yellow]Warning: Empty response received[/yellow]")
            
        except requests.exceptions.Timeout:
            console.print(f"\n[red]✗ Request timed out[/red]")
        except requests.exceptions.ConnectionError as e:
            console.print(f"\n[red]✗ Connection error: Cannot reach server at {API_URL}[/red]")
        except requests.exceptions.RequestException as e:
            console.print(f"\n[red]✗ Request error: {e}[/red]")
        except Exception as e:
            console.print(f"\n[red]✗ Unexpected error: {e}[/red]")
            import traceback
            traceback.print_exc()
    
    def handle_command(self, cmd):
        """Handle special commands"""
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else None
        
        if command == '/help':
            self.show_help()
        
        elif command == '/new':
            self.messages = []
            self.current_conversation_id = None
            console.print("[green]✓ Started new conversation[/green]")
        
        elif command == '/save':
            title = arg if arg else None
            self.save_conversation(title)
        
        elif command == '/load':
            if arg:
                self.load_conversation(arg)
            else:
                console.print("[red]Usage: /load <conversation_id>[/red]")
        
        elif command == '/history':
            self.list_conversations()
        
        elif command == '/project':
            if arg:
                self.create_project(arg)
            else:
                console.print("[red]Usage: /project <name>[/red]")
        
        elif command == '/projects':
            self.list_projects()
        
        elif command == '/show':
            self.display_history()
        
        elif command == '/clear':
            os.system('clear' if os.name != 'nt' else 'cls')
        
        elif command == '/export':
            self.export_markdown()
        
        elif command in ['/exit', '/quit']:
            # Auto-save before exit
            if self.messages:
                self.save_conversation()
            console.print("[cyan]Goodbye! 👋[/cyan]")
            sys.exit(0)
        
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            console.print("[dim]Type /help for available commands[/dim]")
    
    def export_markdown(self):
        """Export conversation to markdown"""
        if not self.messages:
            console.print("[yellow]No messages to export[/yellow]")
            return
        
        filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(filename, 'w') as f:
            f.write(f"# Rick AI Conversation\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if self.current_project:
                f.write(f"Project: {self.current_project}\n\n")
            
            f.write("---\n\n")
            
            for msg in self.messages:
                role = msg['role'].capitalize()
                f.write(f"## {role}\n\n")
                f.write(f"{msg['content']}\n\n")
        
        console.print(f"[green]✓ Exported to:[/green] {filename}")
    
    def show_help(self):
        """Show help message"""
        help_text = """
[bold cyan]Rick AI Commands:[/bold cyan]

[bold]Conversation:[/bold]
  /new              Start a new conversation
  /save [title]     Save current conversation
  /load <id>        Load a conversation
  /history          List recent conversations
  /show             Show current conversation
  /clear            Clear screen
  /export           Export to markdown

[bold]Projects:[/bold]
  /project <name>   Create/switch to project
  /projects         List all projects

[bold]Other:[/bold]
  /help             Show this help
  /exit, /quit      Exit Rick (auto-saves)

[dim]Tip: Just type normally to chat with Rick![/dim]
"""
        console.print(help_text)
    
    def run(self):
        """Main REPL loop"""
        # Show welcome message
        console.print(Panel.fit(
            "[bold cyan]Rick AI[/bold cyan]\n"
            "Your intelligent coding assistant\n\n"
            "[dim]Type /help for commands or just start chatting![/dim]",
            border_style="cyan"
        ))
        
        # Load last project if exists
        if self.config.get('current_project'):
            self.current_project = self.config['current_project']
            console.print(f"[dim]Project: {self.current_project}[/dim]")
        
        console.print()
        
        while True:
            try:
                # Show prompt
                project_indicator = f"[{self.current_project}] " if self.current_project else ""
                user_input = Prompt.ask(f"\n{project_indicator}[green]You[/green]")
                
                if not user_input.strip():
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    self.handle_command(user_input)
                else:
                    # Send message to Rick
                    self.send_message(user_input)
            
            except KeyboardInterrupt:
                console.print("\n[dim]Use /exit to quit[/dim]")
                continue
            except EOFError:
                break

if __name__ == "__main__":
    cli = RickCLI()
    cli.run()
