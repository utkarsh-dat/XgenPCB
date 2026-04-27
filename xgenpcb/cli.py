# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich>=13.7.0",
#     "httpx>=0.27.0",
#     "python-dotenv>=1.0.1",
#     "websockets>=12.0",
# ]
# ///

import asyncio
import httpx
import json
import sys
import os
import websockets
from typing import Optional
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()

XGEN_HOME = os.path.expanduser("~/.xgenpcb")
CONFIG_PATH = os.path.join(XGEN_HOME, "config.json")

# Default to production API (placeholder), but allow override for local dev
API_BASE = os.getenv("XGEN_API_URL", "http://localhost:8000/api/v1")

def save_token(token: str):
    """Save JWT token to local config."""
    os.makedirs(XGEN_HOME, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"access_token": token}, f)

def load_token() -> Optional[str]:
    """Load JWT token from local config."""
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f).get("access_token")
    except:
        return None

async def login(client: httpx.AsyncClient) -> str:
    """Interactively log the user in."""
    console.print("\n[bold cyan]Welcome to XgenPCB![/bold cyan]")
    console.print("Please log in to your account to continue.\n")
    
    email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)
    
    try:
        res = await client.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
        if res.status_code == 200:
            token = res.json()["access_token"]
            save_token(token)
            console.print("[bold green]✔ Login successful![/bold green]\n")
            return token
        elif res.status_code == 401:
            console.print("[bold yellow]Account not found or invalid credentials.[/bold yellow]")
            if Prompt.ask("Would you like to create a new account?", choices=["y", "n"], default="y") == "y":
                full_name = Prompt.ask("Full Name")
                reg_res = await client.post(f"{API_BASE}/auth/register", json={
                    "email": email,
                    "password": password,
                    "full_name": full_name
                })
                if reg_res.status_code == 201:
                    token = reg_res.json()["access_token"]
                    save_token(token)
                    console.print("[bold green]✔ Registration successful! Welcome to XgenPCB.[/bold green]\n")
                    return token
                else:
                    console.print(f"[bold red]Registration failed:[/bold red] {reg_res.text}")
                    sys.exit(1)
            else:
                sys.exit(0)
        else:
            console.print(f"[bold red]Error ({res.status_code}):[/bold red] {res.text}")
            sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error connecting to XgenPCB API:[/bold red] {e}")
        sys.exit(1)

async def get_authenticated_client(client: httpx.AsyncClient) -> str:
    """Get a valid token, logging in if necessary."""
    token = load_token()
    if token:
        # Quick check if token is still valid
        try:
            res = await client.get(f"{API_BASE}/auth/me", headers={"Authorization": f"Bearer {token}"})
            if res.status_code == 200:
                return token
        except:
            pass
            
    # If no token or invalid, force login
    return await login(client)

async def generate_pcb(client: httpx.AsyncClient, token: str, prompt: str):
    # Load keys from local .env if present
    load_dotenv()
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    
    headers = {"Authorization": f"Bearer {token}"}
    if nvidia_key:
        headers["X-NVIDIA-API-KEY"] = nvidia_key
    
    try:
        res = await client.post(
            f"{API_BASE}/ai/generate-pcb",
            json={"input_type": "text", "description": prompt},
            headers=headers
        )
        res.raise_for_status()
        job_id = res.json()["job_id"]
    except Exception as e:
        console.print(f"[bold red]Failed to submit job:[/bold red] {e}")
        return

    # ── Real-time WebSocket Updates ──────────────────────────
    ws_base = API_BASE.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_base}/ai/ws/jobs/{job_id}"
    
    from rich.box import ROUNDED
    from rich.live import Live
    try:
        from rich.group import Group
    except ImportError:
        from rich.console import Group
    from rich.layout import Layout
    
    reasoning_buffer = ""
    
    # Initialize Progress bar
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
        transient=False
    )
    task = progress.add_task("[white]Initializing...", total=100)
    
    def get_ui(buffer):
        """Build the live UI group."""
        if not buffer:
            return progress
        
        return Group(
            Panel(
                f"[italic dim white]{buffer}[/italic dim white]",
                title="[bold dim white]ANALYSIS & STRATEGY[/bold dim white]",
                border_style="dim white",
                box=ROUNDED,
                padding=(0, 2)
            ),
            progress
        )

    try:
        async with websockets.connect(ws_url) as websocket:
            # Use Live to render the combined UI
            with Live(get_ui(""), console=console, refresh_per_second=10) as live:
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        status = data.get("status", "unknown")
                        progress_val = data.get("progress", 0.0) * 100
                        message_text = data.get("message", "Processing...")
                        
                        # ── Handle Live Reasoning Deltas ──────────────
                        delta = data.get("design_reasoning_delta")
                        if delta:
                            reasoning_buffer += delta
                            live.update(get_ui(reasoning_buffer))
                        
                        # Update progress bar
                        progress.update(task, completed=progress_val, description=f"[white]{message_text}")
                        
                        if status == "completed":
                            progress.update(task, description="[bold green]COMPLETE")
                            live.stop()
                            console.print(Panel(
                                f"[bold green]SUCCESS[/bold green]\n\n"
                                f"DESIGN ID: [bold white]{data.get('design_id')}[/bold white]\n"
                                f"LOCATION: [dim]storage/designs/{data.get('design_id')}[/dim]",
                                title="GENERATION RESULT",
                                border_style="green"
                            ))
                            break
                        elif status == "failed":
                            progress.update(task, description="[bold red]FAILED")
                            live.stop()
                            console.print(f"\n[bold red]ERROR:[/bold red] {data.get('error')}")
                            break
                            
                    except websockets.ConnectionClosed:
                        break
    except Exception as e:
        console.print(f"\n[bold red]Connection Error:[/bold red] {e}")
        await asyncio.sleep(2)

async def main():
    # Minimalist header
    console.print("\n[bold white]XGENPCB AGENT[/bold white] [dim]v0.1.0[/dim]")
    console.print("[dim]Submit requirements or type 'exit' to quit.[/dim]\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        token = await get_authenticated_client(client)
        
        while True:
            try:
                user_input = Prompt.ask("[bold white]>[/bold white]")
                if user_input.lower() in ["exit", "quit", "q"]:
                    break
                if not user_input.strip():
                    continue
                
                await generate_pcb(client, token, user_input)
                console.print() # Spacing
                
            except KeyboardInterrupt:
                break

def main_wrapper():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Exiting XgenPCB. Goodbye![/bold yellow]")
        sys.exit(0)

if __name__ == "__main__":
    main_wrapper()
