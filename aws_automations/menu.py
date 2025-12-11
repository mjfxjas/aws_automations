"""Interactive start menu for AWS Automations."""

from __future__ import annotations

import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text

from .main import main as run_cleanup


def show_banner():
    """Display the application banner."""
    console = Console()
    
    banner = Text("AWS AUTOMATIONS", style="bold blue")
    subtitle = Text("Multi-Service Resource Cleanup Tool", style="dim")
    
    console.print()
    console.print(Panel.fit(f"{banner}\n{subtitle}", border_style="blue"))
    console.print()


def show_services_table():
    """Display available services in a table."""
    console = Console()
    
    table = Table(title="Available Services", show_header=True, header_style="bold magenta")
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_column("Resources", style="green")
    
    services = [
        ("s3", "S3 Storage", "Buckets, Objects, Versions"),
        ("ec2", "EC2 Compute", "Instances, Volumes"),
        ("lambda", "Lambda Functions", "Functions, Versions, Logs"),
        ("ebs", "EBS Storage", "Volumes, Snapshots"),
        ("cloudwatch", "CloudWatch", "Log Groups, Streams"),
        ("iam", "Identity & Access", "Roles, Users, Policies"),
        ("all", "All Services", "Complete cleanup across all services")
    ]
    
    for service, desc, resources in services:
        table.add_row(service, desc, resources)
    
    console.print(table)
    console.print()


def get_service_choice() -> str:
    """Get user's service selection."""
    valid_services = ["s3", "ec2", "lambda", "ebs", "cloudwatch", "iam", "all"]
    
    while True:
        choice = Prompt.ask(
            "Select service to clean up",
            choices=valid_services,
            default="all"
        )
        return choice


def get_mode_choice() -> tuple[bool, bool]:
    """Get dry-run and interactive mode choices."""
    console = Console()
    
    console.print("[yellow]Safety Options:[/yellow]")
    
    dry_run = not Confirm.ask("Apply changes (default is dry-run only)", default=False)
    
    if not dry_run:
        console.print("[red]⚠️  DESTRUCTIVE MODE ENABLED[/red]")
        confirm = Confirm.ask("Are you sure you want to delete resources?", default=False)
        if not confirm:
            dry_run = True
            console.print("[green]Switched back to dry-run mode[/green]")
    
    interactive = Confirm.ask("Enable interactive approval", default=False)
    
    return dry_run, interactive


def get_config_path() -> str:
    """Get configuration file path."""
    default_config = "config.yaml"
    
    config_path = Prompt.ask(
        "Configuration file path",
        default=default_config
    )
    
    return config_path


def show_summary(service: str, dry_run: bool, interactive: bool, config: str):
    """Show execution summary."""
    console = Console()
    
    table = Table(title="Execution Summary", show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Service", service)
    table.add_row("Mode", "Dry Run" if dry_run else "[red]APPLY CHANGES[/red]")
    table.add_row("Interactive", "Yes" if interactive else "No")
    table.add_row("Config", config)
    
    console.print(table)
    console.print()


def interactive_menu():
    """Run the interactive menu."""
    console = Console()
    
    try:
        show_banner()
        
        # Service selection
        show_services_table()
        service = get_service_choice()
        
        console.print()
        
        # Mode selection
        dry_run, interactive = get_mode_choice()
        
        console.print()
        
        # Config selection
        config_path = get_config_path()
        
        console.print()
        
        # Summary
        show_summary(service, dry_run, interactive, config_path)
        
        # Final confirmation
        if not Confirm.ask("Proceed with cleanup?", default=True):
            console.print("[yellow]Operation cancelled[/yellow]")
            return
        
        console.print()
        console.print("[green]Starting cleanup...[/green]")
        console.print()
        
        # Build arguments for main function
        args = [
            "--config", config_path,
            "--service", service
        ]
        
        if not dry_run:
            args.append("--apply")
        
        if interactive:
            args.append("--interactive")
        
        # Run the cleanup
        sys.argv = ["aws-cleanup"] + args
        run_cleanup()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")


if __name__ == "__main__":
    interactive_menu()