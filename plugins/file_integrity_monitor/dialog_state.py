"""State and control helpers for the file integrity monitor dialog."""

from __future__ import annotations

class MonitorDialogStateMixin:
    def _load_state(self) -> None:
        for action in (
            self._sync_directory_list,
            self._sync_interval,
            self._sync_auto_scan,
            self._update_status,
            self._update_timer,
        ):
            action()

    def _sync_directory_list(self) -> None:
        self.directory_list.clear()
        if self._controller.directories:
            self.directory_list.addItems(self._controller.directories)

    def _sync_interval(self) -> None:
        self.interval_input.blockSignals(True)
        self.interval_input.setValue(self._controller.interval_minutes)
        self.interval_input.blockSignals(False)

    def _sync_auto_scan(self) -> None:
        self.auto_scan_checkbox.blockSignals(True)
        self.auto_scan_checkbox.setChecked(self._controller.auto_scan_enabled)
        self.auto_scan_checkbox.blockSignals(False)

    def _handle_interval_change(self) -> None:
        self._controller.update_interval(self.interval_input.value())
        if self.scan_timer.isActive():
            self._start_timer()
        self._update_status()

    def _toggle_auto_scan(self) -> None:
        self._controller.toggle_auto_scan(self.auto_scan_checkbox.isChecked())
        self._update_timer()

    def _update_timer(self) -> None:
        enabled = bool(
            self._controller.auto_scan_enabled
            and self._controller.directories
            and self._controller.has_baseline()
        )
        if enabled:
            self._start_timer()
        elif self.scan_timer.isActive():
            self.scan_timer.stop()
        self._update_status()

    def _start_timer(self) -> None:
        self.scan_timer.start(max(1, self._controller.interval_minutes) * 60 * 1000)

    def _update_status(self) -> None:
        if not self._controller.has_baseline():
            text = "Baseline not created"
        elif self._controller.auto_scan_enabled and self._controller.directories:
            text = "Automatic scanning enabled (every %d minutes)" % self._controller.interval_minutes
        else:
            text = "Baseline ready – automatic scanning disabled"
        self.status_label.setText(text)

    def _append_log(self, message: str) -> None:
        self.log_output.append(message)
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())


__all__ = ["MonitorDialogStateMixin"]
