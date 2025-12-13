"""Terminal UI for vidtools"""

import threading
from pathlib import Path
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, ProgressBar,
    Input, Label, DataTable, RichLog, Select, Switch, TextArea
)
from textual.binding import Binding
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

from .compress import (
    probe_video, compress, VideoInfo,
    PRESETS, DEFAULT_PRESET, Preset,
    detect_preset_from_filename,
)
from .watcher import Watcher, WatchFolders, Job, JobStatus
from .config import get_config, get_config_path, reload_config


class VideoInfoPanel(Static):
    """Display video metadata"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._info: VideoInfo | None = None
        self._preset: Preset | None = None

    def update_info(self, info: VideoInfo | None, preset: Preset | None = None):
        self._info = info
        self._preset = preset
        self.refresh()

    def render(self):
        if not self._info:
            return Panel(
                "[dim]No video loaded[/dim]\n\nPaste path below or drop into inbox",
                title="[bold cyan][ INPUT ][/bold cyan]",
                border_style="cyan",
            )

        i = self._info
        preset_str = f"[magenta]{self._preset.name}[/magenta]" if self._preset else "[dim]auto[/dim]"
        content = f"""[bold white]{i.path.name}[/bold white]

[cyan]Dimensions[/cyan]  {i.dimensions}
[cyan]Duration[/cyan]    {i.duration:.1f}s
[cyan]Codec[/cyan]       {i.codec}
[cyan]FPS[/cyan]         {i.fps:.0f}
[cyan]Bitrate[/cyan]     {i.bitrate // 1000} kbps
[cyan]Size[/cyan]        [bold yellow]{i.size_mb:.1f} MB[/bold yellow]
[cyan]Preset[/cyan]      {preset_str}"""

        return Panel(
            content,
            title="[bold cyan][ INPUT ][/bold cyan]",
            border_style="cyan",
        )


class OutputPanel(Static):
    """Display compression results"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._result = None

    def set_result(self, original_mb: float, compressed_mb: float, reduction: float, path: Path, preset_name: str = ""):
        self._result = (original_mb, compressed_mb, reduction, path, preset_name)
        self.refresh()

    def clear(self):
        self._result = None
        self.refresh()

    def render(self):
        if not self._result:
            return Panel(
                "[dim]Waiting for compression...[/dim]",
                title="[bold green][ OUTPUT ][/bold green]",
                border_style="green",
            )

        orig, comp, reduction, path, preset_name = self._result
        content = f"""[bold white]{path.name}[/bold white]

[green]Original[/green]    {orig:.1f} MB
[green]Compressed[/green]  [bold]{comp:.1f} MB[/bold]
[green]Reduction[/green]   [bold yellow]{reduction:.1f}%[/bold yellow]
[green]Preset[/green]      [magenta]{preset_name}[/magenta]"""

        return Panel(
            content,
            title="[bold green][ OUTPUT ][/bold green]",
            border_style="green",
        )


class QueuePanel(Static):
    """Display job queue from watcher"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._jobs: list[Job] = []
        self._watch_path: Path | None = None

    def set_watch_path(self, path: Path):
        self._watch_path = path
        self.refresh()

    def update_jobs(self, jobs: list[Job]):
        self._jobs = jobs
        self.refresh()

    def render(self):
        if not self._watch_path:
            content = "[dim]Watcher not started[/dim]"
        elif not self._jobs:
            content = f"[dim]Watching:[/dim] {self._watch_path}/inbox\n\n[dim]No jobs in queue[/dim]\n\n[dim italic]Drop files with preset suffix:[/dim]\n  video[magenta]-social[/magenta].mp4\n  video[magenta]-web[/magenta].mp4\n  video[magenta]-archive[/magenta].mp4\n  video[magenta]-tiny[/magenta].mp4"
        else:
            lines = [f"[dim]Watching:[/dim] {self._watch_path}/inbox\n"]
            for job in self._jobs[-8:]:  # Show last 8 jobs
                status_icon = {
                    JobStatus.QUEUED: "[yellow]>[/yellow]",
                    JobStatus.PROCESSING: "[cyan]~[/cyan]",
                    JobStatus.DONE: "[green]+[/green]",
                    JobStatus.FAILED: "[red]![/red]",
                }[job.status]

                name = job.input_path.name[:30]
                if len(job.input_path.name) > 30:
                    name = name[:27] + "..."

                if job.status == JobStatus.PROCESSING:
                    pct = f"[cyan]{job.progress*100:3.0f}%[/cyan]"
                    lines.append(f"{status_icon} {name} {pct}")
                elif job.status == JobStatus.DONE and job.result:
                    reduction = f"[green]-{job.result.reduction_percent:.0f}%[/green]"
                    lines.append(f"{status_icon} {name} {reduction}")
                else:
                    lines.append(f"{status_icon} {name}")

            content = "\n".join(lines)

        return Panel(
            content,
            title="[bold magenta][ QUEUE ][/bold magenta]",
            border_style="magenta",
        )


class StatusLog(RichLog):
    """Styled log widget with markup enabled"""

    def __init__(self, **kwargs):
        super().__init__(markup=True, **kwargs)


class ConfigScreen(Screen):
    """Configuration editor screen with simple/advanced modes"""

    CSS = """
    ConfigScreen {
        align: center middle;
    }

    #config-container {
        width: 80%;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #config-header {
        height: 3;
        margin-bottom: 1;
    }

    #config-title {
        width: 1fr;
        text-style: bold;
        color: $text;
        padding: 0 1;
    }

    #mode-toggle {
        width: auto;
    }

    .config-row {
        height: 3;
        margin: 1 0;
    }

    .config-label {
        width: 20;
        padding: 0 1;
    }

    .config-input {
        width: 1fr;
    }

    #simple-mode {
        height: auto;
    }

    #advanced-mode {
        display: none;
        height: auto;
    }

    #advanced-mode.active {
        display: block;
    }

    #simple-mode.hidden {
        display: none;
    }

    #config-editor {
        height: 20;
        margin: 1 0;
    }

    #config-buttons {
        height: 3;
        margin-top: 2;
        align: center middle;
    }

    #config-buttons Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
        Binding("tab", "toggle_mode", "Toggle Mode", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.advanced_mode = False

    def compose(self) -> ComposeResult:
        config = get_config()
        config_path = get_config_path()
        raw_content = config_path.read_text() if config_path.exists() else ""

        with Container(id="config-container"):
            with Horizontal(id="config-header"):
                yield Static("[bold cyan][ CONFIGURATION ][/bold cyan]", id="config-title")
                yield Button("Advanced", id="mode-toggle", variant="default")

            # Simple mode - form inputs
            with Container(id="simple-mode"):
                with Horizontal(classes="config-row"):
                    yield Static("Watch Folder:", classes="config-label")
                    yield Input(
                        str(config.folders.watch_base),
                        id="watch-base-input",
                        classes="config-input",
                    )

                with Horizontal(classes="config-row"):
                    yield Static("Default Preset:", classes="config-label")
                    yield Select(
                        [(name, name) for name in PRESETS.keys()],
                        value=config.presets.default,
                        id="default-preset-select",
                        classes="config-input",
                    )

                with Horizontal(classes="config-row"):
                    yield Static("Auto-start Watcher:", classes="config-label")
                    yield Switch(value=config.behavior.auto_start_watcher, id="auto-start-switch")

                with Horizontal(classes="config-row"):
                    yield Static("Delete Source:", classes="config-label")
                    yield Switch(value=config.behavior.delete_source, id="delete-source-switch")

                with Horizontal(classes="config-row"):
                    yield Static("Notifications:", classes="config-label")
                    yield Switch(value=config.behavior.notifications, id="notifications-switch")

            # Advanced mode - raw TOML editor
            with Container(id="advanced-mode"):
                yield Static(f"[dim]{config_path}[/dim]", id="config-path")
                yield TextArea(raw_content, language="toml", id="config-editor", show_line_numbers=True)

            with Horizontal(id="config-buttons"):
                yield Button("Save", id="save-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
        elif event.button.id == "mode-toggle":
            self.action_toggle_mode()

    def action_toggle_mode(self):
        """Toggle between simple and advanced mode"""
        self.advanced_mode = not self.advanced_mode

        simple = self.query_one("#simple-mode")
        advanced = self.query_one("#advanced-mode")
        toggle_btn = self.query_one("#mode-toggle", Button)

        if self.advanced_mode:
            simple.add_class("hidden")
            advanced.add_class("active")
            toggle_btn.label = "Simple"
            # Sync form values to raw TOML
            self._sync_form_to_editor()
        else:
            simple.remove_class("hidden")
            advanced.remove_class("active")
            toggle_btn.label = "Advanced"

    def _sync_form_to_editor(self):
        """Update raw editor with current form values"""
        watch_base = self.query_one("#watch-base-input", Input).value
        default_preset = self.query_one("#default-preset-select", Select).value
        auto_start = self.query_one("#auto-start-switch", Switch).value
        delete_source = self.query_one("#delete-source-switch", Switch).value
        notifications = self.query_one("#notifications-switch", Switch).value

        content = f'''# vidtools configuration

[folders]
watch_base = "{watch_base}"

[presets]
default = "{default_preset}"

[behavior]
auto_start_watcher = {str(auto_start).lower()}
delete_source = {str(delete_source).lower()}
notifications = {str(notifications).lower()}
'''
        editor = self.query_one("#config-editor", TextArea)
        editor.load_text(content)

    def action_save(self):
        """Save config and return to main screen"""
        if self.advanced_mode:
            # Save raw TOML from editor
            editor = self.query_one("#config-editor", TextArea)
            config_content = editor.text
        else:
            # Build TOML from form
            watch_base = self.query_one("#watch-base-input", Input).value
            default_preset = self.query_one("#default-preset-select", Select).value
            auto_start = self.query_one("#auto-start-switch", Switch).value
            delete_source = self.query_one("#delete-source-switch", Switch).value
            notifications = self.query_one("#notifications-switch", Switch).value

            config_content = f'''# vidtools configuration

[folders]
watch_base = "{watch_base}"

[presets]
default = "{default_preset}"

[behavior]
auto_start_watcher = {str(auto_start).lower()}
delete_source = {str(delete_source).lower()}
notifications = {str(notifications).lower()}
'''

        # Write to file
        config_path = get_config_path()
        config_path.write_text(config_content)

        # Reload config
        reload_config()

        self.app.pop_screen()
        self.app.notify("Config saved!", severity="information")

    def action_cancel(self):
        """Return to main screen without saving"""
        self.app.pop_screen()


class VidToolsApp(App):
    """Video compression TUI"""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        height: 100%;
        padding: 1;
    }

    #top-panels {
        height: auto;
        max-height: 14;
    }

    VideoInfoPanel, OutputPanel {
        width: 1fr;
        height: auto;
        min-height: 12;
        margin: 0 1;
    }

    #queue-row {
        height: auto;
        max-height: 14;
        margin: 0 1;
    }

    QueuePanel {
        width: 100%;
        height: auto;
        min-height: 10;
    }

    #input-row {
        height: 3;
        margin: 1;
        padding: 0 1;
    }

    #file-input {
        width: 2fr;
    }

    #preset-select {
        width: 1fr;
    }

    #progress-container {
        height: 3;
        margin: 1;
        padding: 0 1;
        display: none;
    }

    #progress-container.active {
        display: block;
    }

    ProgressBar {
        width: 100%;
    }

    #button-row {
        height: 3;
        margin: 1;
        padding: 0 1;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    #compress-btn {
        background: $success;
    }

    #watch-btn {
        background: $warning;
    }

    #log-container {
        height: 1fr;
        margin: 1;
        border: solid $primary;
    }

    StatusLog {
        height: 100%;
        background: $surface-darken-1;
    }
    """

    BINDINGS = [
        Binding("escape", "unfocus", "Unfocus", show=False),
        Binding("q", "quit", "Quit"),
        Binding("c", "compress", "Compress"),
        Binding("w", "toggle_watch", "Watch"),
        Binding("e", "open_config", "Config"),
        Binding("ctrl+l", "clear_log", "Clear Log"),
    ]

    def __init__(self):
        super().__init__()
        self.video_info: VideoInfo | None = None
        self.selected_preset: Preset = DEFAULT_PRESET
        self.watcher: Watcher | None = None
        self.watch_folders: WatchFolders | None = None
        self._last_escape: float = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            with Horizontal(id="top-panels"):
                yield VideoInfoPanel(id="info-panel")
                yield OutputPanel(id="output-panel")

            with Container(id="queue-row"):
                yield QueuePanel(id="queue-panel")

            with Horizontal(id="input-row"):
                yield Input(placeholder="Enter video path...", id="file-input")
                yield Select(
                    [(f"{p.name} - {p.description[:30]}", p.name) for p in PRESETS.values()],
                    value="social",
                    id="preset-select",
                )
                yield Button("Load", id="load-btn", variant="primary")

            with Horizontal(id="progress-container"):
                yield ProgressBar(id="progress", show_eta=True)

            with Horizontal(id="button-row"):
                yield Button("Compress", id="compress-btn", variant="success", disabled=True)
                yield Button("Start Watcher", id="watch-btn", variant="warning")

            with Container(id="log-container"):
                yield StatusLog(id="log", highlight=True)

        yield Footer()

    def on_mount(self):
        self.title = "vidtools"
        self.sub_title = "video compression utility"
        log = self.query_one("#log", StatusLog)
        config = get_config()
        log.write("[bold cyan]vidtools[/bold cyan] v0.1.0")
        log.write(f"[dim]Config: {get_config_path()}[/dim]")
        log.write(f"[dim]Watch folder: {config.folders.watch_base}[/dim]")
        log.write(f"[dim]Presets: {', '.join(PRESETS.keys())} | Press [bold]e[/bold] to edit config[/dim]")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "load-btn":
            self.action_load_video()
        elif event.button.id == "compress-btn":
            self.action_compress()
        elif event.button.id == "watch-btn":
            self.action_toggle_watch()

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "file-input":
            self.action_load_video()

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "preset-select":
            self.selected_preset = PRESETS[event.value]
            if self.video_info:
                info_panel = self.query_one("#info-panel", VideoInfoPanel)
                info_panel.update_info(self.video_info, self.selected_preset)

    def action_load_video(self):
        file_input = self.query_one("#file-input", Input)
        path_str = file_input.value.strip()

        if not path_str:
            return

        path = Path(path_str).expanduser().resolve()
        log = self.query_one("#log", StatusLog)

        if not path.exists():
            log.write(f"[red]Error:[/red] File not found: {path}")
            return

        try:
            log.write(f"[cyan]Probing:[/cyan] {path.name}")
            self.video_info = probe_video(path)

            # Auto-detect preset from filename
            detected = detect_preset_from_filename(path)
            if detected:
                self.selected_preset = detected
                select = self.query_one("#preset-select", Select)
                select.value = detected.name
                log.write(f"[magenta]Preset detected:[/magenta] {detected.name}")

            info_panel = self.query_one("#info-panel", VideoInfoPanel)
            info_panel.update_info(self.video_info, self.selected_preset)

            output_panel = self.query_one("#output-panel", OutputPanel)
            output_panel.clear()

            compress_btn = self.query_one("#compress-btn", Button)
            compress_btn.disabled = False

            log.write(f"[green]Loaded:[/green] {self.video_info.dimensions}, {self.video_info.size_mb:.1f} MB")

        except Exception as e:
            log.write(f"[red]Error:[/red] {e}")

    def action_compress(self):
        if not self.video_info:
            return

        log = self.query_one("#log", StatusLog)
        progress_container = self.query_one("#progress-container")
        progress = self.query_one("#progress", ProgressBar)
        compress_btn = self.query_one("#compress-btn", Button)

        compress_btn.disabled = True
        progress_container.add_class("active")
        progress.update(total=100, progress=0)

        preset = self.selected_preset
        log.write(f"[yellow]Compressing:[/yellow] {self.video_info.path.name}")
        log.write(f"[dim]  Preset: {preset.name} | Scale: {preset.scale*100:.0f}% | CRF: {preset.crf}[/dim]")

        def on_progress(p: float):
            self.call_from_thread(progress.update, progress=p * 100)

        def do_compress():
            try:
                result = compress(
                    self.video_info.path,
                    preset=preset,
                    on_progress=on_progress,
                )

                def finish():
                    progress.update(progress=100)
                    progress_container.remove_class("active")
                    output_panel = self.query_one("#output-panel", OutputPanel)
                    output_panel.set_result(
                        result.original_size / (1024 * 1024),
                        result.compressed_size / (1024 * 1024),
                        result.reduction_percent,
                        result.output_path,
                        preset.name,
                    )
                    log.write(f"[green]Done![/green] {result.output_path}")
                    log.write(f"[green]Reduced:[/green] {result.reduction_percent:.1f}%")
                    compress_btn.disabled = False

                self.call_from_thread(finish)

            except Exception as e:
                def error():
                    progress_container.remove_class("active")
                    log.write(f"[red]Error:[/red] {e}")
                    compress_btn.disabled = False

                self.call_from_thread(error)

        thread = threading.Thread(target=do_compress, daemon=True)
        thread.start()

    def action_toggle_watch(self):
        log = self.query_one("#log", StatusLog)
        watch_btn = self.query_one("#watch-btn", Button)
        queue_panel = self.query_one("#queue-panel", QueuePanel)

        if self.watcher and self.watcher.is_running:
            # Stop watcher
            self.watcher.stop()
            watch_btn.label = "Start Watcher"
            log.write("[yellow]Watcher stopped[/yellow]")
        else:
            # Start watcher
            config = get_config()
            watch_base = config.folders.watch_base
            self.watch_folders = WatchFolders.create(watch_base)
            queue_panel.set_watch_path(watch_base)

            def on_job_added(job: Job):
                def update():
                    queue_panel.update_jobs(self.watcher.jobs)
                    log.write(f"[cyan]Queued:[/cyan] {job.input_path.name} [{job.preset.name}]")
                self.call_from_thread(update)

            def on_job_updated(job: Job):
                def update():
                    queue_panel.update_jobs(self.watcher.jobs)
                self.call_from_thread(update)

            def on_job_done(job: Job):
                def update():
                    queue_panel.update_jobs(self.watcher.jobs)
                    if job.status == JobStatus.DONE and job.result:
                        log.write(f"[green]Completed:[/green] {job.result.output_path.name} (-{job.result.reduction_percent:.1f}%)")
                    elif job.status == JobStatus.FAILED:
                        log.write(f"[red]Failed:[/red] {job.input_path.name} - {job.error}")
                self.call_from_thread(update)

            self.watcher = Watcher(
                self.watch_folders,
                on_job_added=on_job_added,
                on_job_updated=on_job_updated,
                on_job_done=on_job_done,
            )
            self.watcher.start()

            watch_btn.label = "Stop Watcher"
            log.write(f"[green]Watcher started[/green]")
            log.write(f"[dim]Inbox: {self.watch_folders.inbox}[/dim]")
            log.write(f"[dim]Output: {self.watch_folders.done}[/dim]")

    def action_unfocus(self):
        """Return to command mode, double-tap to quit"""
        import time
        now = time.time()

        # If already unfocused and escape pressed twice within 0.5s, quit
        if self.focused is None and (now - self._last_escape) < 0.5:
            self.exit()
            return

        self._last_escape = now
        self.set_focus(None)

    def action_clear_log(self):
        log = self.query_one("#log", StatusLog)
        log.clear()

    def action_open_config(self):
        """Open config editor screen"""
        self.push_screen(ConfigScreen())

    def on_unmount(self):
        if self.watcher:
            self.watcher.stop()


def main():
    app = VidToolsApp()
    app.run()


if __name__ == "__main__":
    main()
