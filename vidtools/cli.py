"""Command-line interface for vidtools"""

import typer
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table

from .compress import probe_video, compress

app = typer.Typer(
    name="vid",
    help="Video compression utilities",
    add_completion=False,
)
console = Console()


@app.command()
def info(path: Path = typer.Argument(..., help="Video file path")):
    """Show video file information"""
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {path}")
        raise typer.Exit(1)

    info = probe_video(path)

    table = Table(title=f"[bold]{path.name}[/bold]", show_header=False, box=None)
    table.add_column(style="cyan")
    table.add_column(style="white")

    table.add_row("Dimensions", info.dimensions)
    table.add_row("Duration", f"{info.duration:.1f}s")
    table.add_row("Codec", info.codec)
    table.add_row("FPS", f"{info.fps:.0f}")
    table.add_row("Bitrate", f"{info.bitrate // 1000} kbps")
    table.add_row("Size", f"[bold yellow]{info.size_mb:.1f} MB[/bold yellow]")

    console.print(table)


@app.command()
def comp(
    path: Path = typer.Argument(..., help="Video file to compress"),
    output: Path | None = typer.Option(None, "-o", "--output", help="Output path"),
    scale: float = typer.Option(0.5, "-s", "--scale", help="Scale factor (0.5 = half)"),
    crf: int = typer.Option(28, "-q", "--crf", help="Quality (0-51, higher = smaller)"),
):
    """Compress a video for sharing"""
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {path}")
        raise typer.Exit(1)

    info = probe_video(path)
    console.print(f"[cyan]Input:[/cyan] {path.name} ({info.size_mb:.1f} MB, {info.dimensions})")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Compressing...", total=100)

        def on_progress(p: float):
            progress.update(task, completed=p * 100)

        result = compress(
            path,
            output_path=output,
            scale=scale,
            crf=crf,
            on_progress=on_progress,
        )

    # Results
    console.print()
    table = Table(show_header=False, box=None)
    table.add_column(style="green")
    table.add_column(style="white")
    table.add_row("Output", str(result.output_path))
    table.add_row("Original", f"{result.original_size / (1024*1024):.1f} MB")
    table.add_row("Compressed", f"[bold]{result.compressed_size / (1024*1024):.1f} MB[/bold]")
    table.add_row("Reduction", f"[bold yellow]{result.reduction_percent:.1f}%[/bold yellow]")
    console.print(table)


@app.command()
def tui():
    """Launch the interactive TUI"""
    from .tui import main
    main()


if __name__ == "__main__":
    app()
