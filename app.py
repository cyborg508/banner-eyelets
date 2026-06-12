import json
import os
import sys
from typing import List, Tuple

import fitz  # PyMuPDF
from PySide6.QtCore import Qt

from banner_eyelets.geometry import (
    cm_to_pt, pt_to_cm, evenly_spaced_positions, build_eyelet_points,
    POINTS_PER_CM,
)
from banner_eyelets.models import BannerSpec, RenderConfig, DEFAULT_SETTINGS
from banner_eyelets.pdf_ops import draw_cross, draw_frame
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

PREVIEW_MAX_WIDTH = 700
PREVIEW_MAX_HEIGHT = 420
SCALE_50_FACTOR = 0.5
SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.json")


def load_settings() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = DEFAULT_SETTINGS.copy()
        merged.update(data)
        return merged
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


class DropArea(QLabel):
    def __init__(self, on_file_selected):
        super().__init__("Przeciągnij tutaj plik PDF\nalbo kliknij 'Otwórz PDF'")
        self.on_file_selected = on_file_selected
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setStyleSheet(
            "border: 2px dashed #888; padding: 24px; font-size: 16px; min-height: 110px;"
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].toLocalFile().lower().endswith(".pdf"):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.on_file_selected(path)
            event.acceptProposedAction()


class PointsPreviewDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Podgląd punktów")
        self.resize(520, 640)
        layout = QVBoxLayout(self)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

    def set_content(self, content: str):
        self.text.setPlainText(content)


class PreferencesDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.resize(460, 380)
        self._starting_settings = settings.copy()
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.margin_input = QLineEdit(str(settings["margin_cm"]))
        self.spacing_input = QLineEdit(str(settings["spacing_cm"]))
        self.marker_input = QLineEdit(str(settings["marker_size_cm"]))
        self.wrap_extra_input = QLineEdit(str(settings["wrap_extra_cm"]))
        self.frame_width_input = QLineEdit(str(settings["frame_base_width_pt"]))
        self.cross_outline_input = QLineEdit(str(settings["cross_outline_multiplier"]))
        self.cross_inner_input = QLineEdit(str(settings["cross_inner_multiplier"]))
        self.border_checkbox = QCheckBox("Domyślnie obramówka")
        self.border_checkbox.setChecked(bool(settings["border_enabled"]))
        self.wrap_checkbox = QCheckBox("Domyślnie zawinięcie")
        self.wrap_checkbox.setChecked(bool(settings["wrap_enabled"]))
        self.half_scale_checkbox = QCheckBox("Domyślnie 50%")
        self.half_scale_checkbox.setChecked(bool(settings["half_scale_enabled"]))

        form.addRow("Domyślny margines oczek [cm]", self.margin_input)
        form.addRow("Domyślny odstęp oczek [cm]", self.spacing_input)
        form.addRow("Domyślny rozmiar krzyżyka [cm]", self.marker_input)
        form.addRow("Domyślne zawinięcie na stronę [cm]", self.wrap_extra_input)
        form.addRow("Domyślna grubość bazowa ramki [pt]", self.frame_width_input)
        form.addRow("Mnożnik obwódki krzyżyka", self.cross_outline_input)
        form.addRow("Mnożnik środka krzyżyka", self.cross_inner_input)
        form.addRow(self.border_checkbox)
        form.addRow(self.wrap_checkbox)
        form.addRow(self.half_scale_checkbox)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        reset_btn = QPushButton("Przywróć domyślne")
        save_btn = QPushButton("Zapisz")
        cancel_btn = QPushButton("Anuluj")
        reset_btn.clicked.connect(self.reset_defaults)
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(reset_btn)
        button_row.addWidget(save_btn)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

    def reset_defaults(self):
        defaults = DEFAULT_SETTINGS
        self.margin_input.setText(str(defaults["margin_cm"]))
        self.spacing_input.setText(str(defaults["spacing_cm"]))
        self.marker_input.setText(str(defaults["marker_size_cm"]))
        self.wrap_extra_input.setText(str(defaults["wrap_extra_cm"]))
        self.frame_width_input.setText(str(defaults["frame_base_width_pt"]))
        self.cross_outline_input.setText(str(defaults["cross_outline_multiplier"]))
        self.cross_inner_input.setText(str(defaults["cross_inner_multiplier"]))
        self.border_checkbox.setChecked(bool(defaults["border_enabled"]))
        self.wrap_checkbox.setChecked(bool(defaults["wrap_enabled"]))
        self.half_scale_checkbox.setChecked(bool(defaults["half_scale_enabled"]))

    def get_settings(self) -> dict:
        return {
            "margin_cm": float(self.margin_input.text().replace(',', '.')),
            "spacing_cm": float(self.spacing_input.text().replace(',', '.')),
            "marker_size_cm": float(self.marker_input.text().replace(',', '.')),
            "wrap_extra_cm": float(self.wrap_extra_input.text().replace(',', '.')),
            "frame_base_width_pt": float(self.frame_width_input.text().replace(',', '.')),
            "cross_outline_multiplier": float(self.cross_outline_input.text().replace(',', '.')),
            "cross_inner_multiplier": float(self.cross_inner_input.text().replace(',', '.')),
            "border_enabled": self.border_checkbox.isChecked(),
            "wrap_enabled": self.wrap_checkbox.isChecked(),
            "half_scale_enabled": self.half_scale_checkbox.isChecked(),
        }


HELP_TEXT = """Banner Eyelets — instrukcja\n\n1. Otwórz lub przeciągnij jednostronicowy plik PDF.\n2. Sprawdź wymiar wejściowy odczytany z pliku.\n3. Ustaw wymiar wyjściowy. Jeśli go nie zmienisz, program użyje rozmiaru PDF.\n4. Ustaw margines oczek, docelowy odstęp i rozmiar krzyżyka.\n5. Opcjonalnie zaznacz:\n   - Obramówka — doda ramkę bazowego formatu wyjściowego\n   - Zawinięcie — doda po ustawionej wartości na stronę i drugą zewnętrzną ramkę\n   - 50% — zmniejszy dodatki technologiczne o połowę przy zachowaniu wymiaru wyjściowego\n6. Użyj przycisku 'Przelicz punkty', aby odświeżyć podgląd.\n7. Użyj 'Podgląd punktów', aby otworzyć osobne okno z listą oczek.\n8. Kliknij 'Generuj PDF z oczkami', aby zapisać plik wynikowy.\n\nUwagi:\n- PDF wejściowy powinien mieć jedną stronę.\n- Grafika wejściowa jest centrowana bez skalowania.\n- Jeśli wymiar wyjściowy jest mniejszy od wejściowego, część grafiki może zostać ucięta.\n"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Banner Eyelets")
        self.resize(980, 960)

        self.settings = load_settings()
        self.pdf_path = None
        self.pdf_width_pt = None
        self.pdf_height_pt = None
        self.input_width_cm = None
        self.input_height_cm = None
        self.points_dialog = PointsPreviewDialog(self)
        self.last_points_preview_text = ""

        self._build_ui()
        self.apply_settings_to_ui()

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)

        self.drop_area = DropArea(self.load_pdf)
        root.addWidget(self.drop_area)

        button_row = QHBoxLayout()
        open_btn = QPushButton("Otwórz PDF")
        open_btn.clicked.connect(self.open_pdf_dialog)
        generate_btn = QPushButton("Generuj PDF z oczkami")
        generate_btn.clicked.connect(self.generate_output)
        preview_btn = QPushButton("Przelicz punkty")
        preview_btn.clicked.connect(self.refresh_preview)
        points_btn = QPushButton("Podgląd punktów")
        points_btn.clicked.connect(self.show_points_preview)
        button_row.addWidget(open_btn)
        button_row.addWidget(generate_btn)
        button_row.addWidget(preview_btn)
        button_row.addWidget(points_btn)
        root.addLayout(button_row)

        info_box = QGroupBox("Informacje o pliku")
        info_layout = QFormLayout(info_box)
        self.file_label = QLabel("—")
        self.page_label = QLabel("—")
        self.pdf_size_label = QLabel("—")
        info_layout.addRow("Plik:", self.file_label)
        info_layout.addRow("Strony:", self.page_label)
        info_layout.addRow("Rozmiar z PDF:", self.pdf_size_label)
        root.addWidget(info_box)

        settings_box = QGroupBox("Ustawienia")
        settings_grid = QGridLayout(settings_box)
        self.input_width_label = QLabel("—")
        self.input_height_label = QLabel("—")
        self.output_width_input = QLineEdit()
        self.output_height_input = QLineEdit()
        self.margin_input = QLineEdit()
        self.spacing_input = QLineEdit()
        self.marker_input = QLineEdit()
        self.border_checkbox = QCheckBox("Obramówka")
        self.wrap_checkbox = QCheckBox("Zawinięcie")
        self.half_scale_checkbox = QCheckBox("50%")
        self.wrap_checkbox.toggled.connect(self.on_wrap_toggled)
        self.centering_label = QLabel("Plik wejściowy będzie wycentrowany na formacie wyjściowym bez skalowania.")
        self.centering_label.setWordWrap(True)

        settings_grid.addWidget(QLabel("Wejście szerokość [cm]"), 0, 0)
        settings_grid.addWidget(self.input_width_label, 0, 1)
        settings_grid.addWidget(QLabel("Wejście wysokość [cm]"), 0, 2)
        settings_grid.addWidget(self.input_height_label, 0, 3)
        settings_grid.addWidget(QLabel("Wyjście szerokość [cm]"), 1, 0)
        settings_grid.addWidget(self.output_width_input, 1, 1)
        settings_grid.addWidget(QLabel("Wyjście wysokość [cm]"), 1, 2)
        settings_grid.addWidget(self.output_height_input, 1, 3)
        settings_grid.addWidget(QLabel("Margines oczek [cm]"), 2, 0)
        settings_grid.addWidget(self.margin_input, 2, 1)
        settings_grid.addWidget(QLabel("Docelowy odstęp [cm]"), 2, 2)
        settings_grid.addWidget(self.spacing_input, 2, 3)
        settings_grid.addWidget(QLabel("Rozmiar krzyżyka [cm]"), 3, 0)
        settings_grid.addWidget(self.marker_input, 3, 1)
        settings_grid.addWidget(self.border_checkbox, 4, 0, 1, 1)
        settings_grid.addWidget(self.wrap_checkbox, 4, 1, 1, 1)
        settings_grid.addWidget(self.half_scale_checkbox, 4, 2, 1, 1)
        settings_grid.addWidget(self.centering_label, 5, 0, 1, 4)
        root.addWidget(settings_box)

        image_box = QGroupBox("Podgląd pliku")
        image_layout = QVBoxLayout(image_box)
        self.preview_image_label = QLabel("Brak podglądu")
        self.preview_image_label.setAlignment(Qt.AlignCenter)
        self.preview_image_label.setStyleSheet("background: #ddd; border: 1px solid #aaa; padding: 8px;")
        self.preview_image_label.setMinimumHeight(280)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.preview_image_label)
        image_layout.addWidget(scroll)
        root.addWidget(image_box)

        self.setCentralWidget(central)

        file_menu = self.menuBar().addMenu("File")
        preferences_menu = self.menuBar().addMenu("Preferences")
        help_menu = self.menuBar().addMenu("Help")

        open_action = QAction("Otwórz PDF", self)
        open_action.triggered.connect(self.open_pdf_dialog)
        file_menu.addAction(open_action)

        generate_action = QAction("Generuj PDF z oczkami", self)
        generate_action.triggered.connect(self.generate_output)
        file_menu.addAction(generate_action)

        file_menu.addSeparator()
        exit_action = QAction("Zamknij", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        preferences_action = QAction("Ustawienia domyślne", self)
        preferences_action.triggered.connect(self.show_preferences)
        preferences_menu.addAction(preferences_action)

        help_action = QAction("Instrukcja używania", self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

        for widget in [
            self.output_width_input,
            self.output_height_input,
            self.margin_input,
            self.spacing_input,
            self.marker_input,
        ]:
            widget.editingFinished.connect(self.refresh_preview)
        self.border_checkbox.toggled.connect(self.refresh_preview)
        self.half_scale_checkbox.toggled.connect(self.refresh_preview)

    def apply_settings_to_ui(self):
        self.margin_input.setText(str(self.settings["margin_cm"]))
        self.spacing_input.setText(str(self.settings["spacing_cm"]))
        self.marker_input.setText(str(self.settings["marker_size_cm"]))
        self.border_checkbox.setChecked(bool(self.settings["border_enabled"]))
        self.wrap_checkbox.setChecked(bool(self.settings["wrap_enabled"]))
        self.half_scale_checkbox.setChecked(bool(self.settings["half_scale_enabled"]))

    def show_help(self):
        QMessageBox.information(self, "Instrukcja używania", HELP_TEXT)

    def show_preferences(self):
        dialog = PreferencesDialog(self.settings, self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.settings = dialog.get_settings()
        except ValueError:
            QMessageBox.critical(self, "Błąd", "W preferencjach wszystkie pola liczbowe muszą być poprawnymi liczbami.")
            return
        save_settings(self.settings)
        self.apply_settings_to_ui()
        self.refresh_preview()

    def get_render_config(self, spec: BannerSpec) -> RenderConfig:
        factor = SCALE_50_FACTOR if self.half_scale_checkbox.isChecked() else 1.0
        scaled_margin_cm = spec.margin_cm * factor
        scaled_spacing_cm = spec.target_spacing_cm * factor
        scaled_marker_size_cm = spec.marker_size_cm * factor
        wrap_extra_cm = self.settings.get("wrap_extra_cm", DEFAULT_SETTINGS["wrap_extra_cm"])
        scaled_wrap_cm = (wrap_extra_cm * factor) if self.wrap_checkbox.isChecked() else 0.0
        final_width_cm = spec.output_width_cm + 2 * scaled_wrap_cm
        final_height_cm = spec.output_height_cm + 2 * scaled_wrap_cm
        return RenderConfig(
            scaled_margin_cm=scaled_margin_cm,
            scaled_spacing_cm=scaled_spacing_cm,
            scaled_marker_size_cm=scaled_marker_size_cm,
            scaled_wrap_cm=scaled_wrap_cm,
            final_width_cm=final_width_cm,
            final_height_cm=final_height_cm,
            scale_mode_label="50%" if self.half_scale_checkbox.isChecked() else "100%",
        )

    def open_pdf_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz PDF", "", "PDF Files (*.pdf)")
        if path:
            self.load_pdf(path)

    def load_pdf(self, path: str):
        try:
            doc = fitz.open(path)
        except Exception as exc:
            QMessageBox.critical(self, "Błąd", f"Nie udało się otworzyć PDF:\n{exc}")
            return

        if doc.page_count != 1:
            QMessageBox.warning(self, "Uwaga", "PDF powinien mieć dokładnie jedną stronę.")

        page = doc[0]
        rect = page.rect
        self.pdf_path = path
        self.pdf_width_pt = rect.width
        self.pdf_height_pt = rect.height

        width_cm = pt_to_cm(rect.width)
        height_cm = pt_to_cm(rect.height)
        self.input_width_cm = width_cm
        self.input_height_cm = height_cm

        self.file_label.setText(os.path.basename(path))
        self.page_label.setText(str(doc.page_count))
        self.pdf_size_label.setText(f"{width_cm:.2f} × {height_cm:.2f} cm")
        self.input_width_label.setText(f"{width_cm:.2f}")
        self.input_height_label.setText(f"{height_cm:.2f}")
        self.output_width_input.setText(f"{width_cm:.2f}")
        self.output_height_input.setText(f"{height_cm:.2f}")
        self.drop_area.setText(f"Załadowano:\n{path}")
        self.refresh_preview()
        doc.close()

    def on_wrap_toggled(self, checked: bool):
        if checked:
            self.border_checkbox.setChecked(True)
        self.refresh_preview()

    def get_spec(self) -> BannerSpec:
        if self.input_width_cm is None or self.input_height_cm is None:
            raise ValueError("Najpierw wczytaj plik PDF.")
        try:
            return BannerSpec(
                input_width_cm=self.input_width_cm,
                input_height_cm=self.input_height_cm,
                output_width_cm=float(self.output_width_input.text().replace(',', '.')),
                output_height_cm=float(self.output_height_input.text().replace(',', '.')),
                margin_cm=float(self.margin_input.text().replace(',', '.')),
                target_spacing_cm=float(self.spacing_input.text().replace(',', '.')),
                marker_size_cm=float(self.marker_input.text().replace(',', '.')),
            )
        except ValueError:
            raise ValueError("Wszystkie pola ustawień muszą być liczbami.")

    def refresh_preview(self):
        try:
            spec = self.get_spec()
            render = self.get_render_config(spec)
            points = build_eyelet_points(
                spec.output_width_cm,
                spec.output_height_cm,
                render.scaled_margin_cm,
                render.scaled_spacing_cm,
            )
        except Exception as exc:
            self.last_points_preview_text = f"Błąd: {exc}"
            self.points_dialog.set_content(self.last_points_preview_text)
            self.preview_image_label.setText("Brak podglądu")
            self.preview_image_label.setPixmap(QPixmap())
            return

        lines = [
            f"Tryb skali technologicznej: {render.scale_mode_label}",
            f"Wymiar wejściowy: {spec.input_width_cm:.2f} × {spec.input_height_cm:.2f} cm",
            f"Wymiar bazowy wyjściowy: {spec.output_width_cm:.2f} × {spec.output_height_cm:.2f} cm",
            f"Wymiar finalnego PDF: {render.final_width_cm:.2f} × {render.final_height_cm:.2f} cm",
            f"Obramówka: {'tak' if self.border_checkbox.isChecked() else 'nie'}",
            f"Zawinięcie: {'tak' if self.wrap_checkbox.isChecked() else 'nie'}",
            f"Skalowany margines oczek: {render.scaled_margin_cm:.2f} cm",
            f"Skalowany odstęp oczek: {render.scaled_spacing_cm:.2f} cm",
            f"Skalowany rozmiar krzyżyka: {render.scaled_marker_size_cm:.2f} cm",
            f"Skalowane zawinięcie na stronę: {render.scaled_wrap_cm:.2f} cm",
            f"Liczba oczek: {len(points)}",
            "",
        ]
        for idx, (x, y) in enumerate(points, start=1):
            lines.append(f"{idx:>3}. x={x:.2f} cm, y={y:.2f} cm")
        self.last_points_preview_text = "\n".join(lines)
        self.points_dialog.set_content(self.last_points_preview_text)
        self.update_image_preview(spec, render, points)

    def show_points_preview(self):
        if not self.last_points_preview_text:
            self.refresh_preview()
        self.points_dialog.set_content(self.last_points_preview_text or "Brak danych do podglądu.")
        self.points_dialog.show()
        self.points_dialog.raise_()
        self.points_dialog.activateWindow()

    def update_image_preview(self, spec: BannerSpec, render: RenderConfig, points: List[Tuple[float, float]]):
        if not self.pdf_path:
            self.preview_image_label.setText("Brak podglądu")
            self.preview_image_label.setPixmap(QPixmap())
            return

        try:
            src_doc = fitz.open(self.pdf_path)
            src_page = src_doc[0]
            pix = src_page.get_pixmap(alpha=False)
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
            src_doc.close()
        except Exception:
            self.preview_image_label.setText("Nie udało się wygenerować podglądu")
            self.preview_image_label.setPixmap(QPixmap())
            return

        scale = min(PREVIEW_MAX_WIDTH / render.final_width_cm, PREVIEW_MAX_HEIGHT / render.final_height_cm)
        canvas_w = max(1, int(render.final_width_cm * scale))
        canvas_h = max(1, int(render.final_height_cm * scale))

        canvas = QPixmap(canvas_w, canvas_h)
        canvas.fill(Qt.white)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.Antialiasing)

        base_left = render.scaled_wrap_cm * scale
        base_top = render.scaled_wrap_cm * scale
        base_w = spec.output_width_cm * scale
        base_h = spec.output_height_cm * scale

        input_w = spec.input_width_cm * scale
        input_h = spec.input_height_cm * scale
        input_left = base_left + (base_w - input_w) / 2.0
        input_top = base_top + (base_h - input_h) / 2.0

        page_pixmap = QPixmap.fromImage(image).scaled(
            max(1, int(round(input_w))),
            max(1, int(round(input_h))),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
        painter.drawPixmap(int(round(input_left)), int(round(input_top)), page_pixmap)

        frame_base_width_pt = self.settings.get("frame_base_width_pt", DEFAULT_SETTINGS["frame_base_width_pt"])
        frame_preview_black = max(2, int(round(frame_base_width_pt)))
        frame_preview_white = max(5, int(round(frame_base_width_pt * 2.2)))

        if self.wrap_checkbox.isChecked():
            painter.setPen(QPen(Qt.white, frame_preview_white))
            painter.drawRect(0, 0, canvas_w - 1, canvas_h - 1)
            painter.setPen(QPen(Qt.black, frame_preview_black))
            painter.drawRect(0, 0, canvas_w - 1, canvas_h - 1)

        if self.border_checkbox.isChecked() or self.wrap_checkbox.isChecked():
            inner_x = int(round(base_left))
            inner_y = int(round(base_top))
            inner_w = max(1, int(round(base_w)))
            inner_h = max(1, int(round(base_h)))
            painter.setPen(QPen(Qt.white, frame_preview_white))
            painter.drawRect(inner_x, inner_y, inner_w, inner_h)
            painter.setPen(QPen(Qt.black, frame_preview_black))
            painter.drawRect(inner_x, inner_y, inner_w, inner_h)

        painter.setPen(QPen(Qt.blue, 1, Qt.DashLine))
        painter.drawRect(int(round(input_left)), int(round(input_top)), max(1, int(round(input_w))), max(1, int(round(input_h))))

        cross_outline_multiplier = self.settings.get("cross_outline_multiplier", DEFAULT_SETTINGS["cross_outline_multiplier"])
        cross_inner_multiplier = self.settings.get("cross_inner_multiplier", DEFAULT_SETTINGS["cross_inner_multiplier"])
        for x_cm, y_cm in points:
            x = base_left + x_cm * scale
            y = base_top + (spec.output_height_cm - y_cm) * scale
            half = max(3.0, render.scaled_marker_size_cm * scale / 2.0)
            outline_width = max(4, int(round(max(5.5, render.scaled_marker_size_cm * scale * cross_outline_multiplier))))
            inner_width = max(2, int(round(max(2.0, render.scaled_marker_size_cm * scale * cross_inner_multiplier))))
            painter.setPen(QPen(Qt.white, outline_width))
            painter.drawLine(int(round(x - half)), int(round(y)), int(round(x + half)), int(round(y)))
            painter.drawLine(int(round(x)), int(round(y - half)), int(round(x)), int(round(y + half)))
            painter.setPen(QPen(Qt.black, inner_width))
            painter.drawLine(int(round(x - half)), int(round(y)), int(round(x + half)), int(round(y)))
            painter.drawLine(int(round(x)), int(round(y - half)), int(round(x)), int(round(y + half)))

        painter.end()
        self.preview_image_label.setPixmap(canvas)
        self.preview_image_label.setText("")

    def generate_output(self):
        if not self.pdf_path:
            QMessageBox.information(self, "Brak pliku", "Najpierw wczytaj plik PDF.")
            return

        try:
            spec = self.get_spec()
            render = self.get_render_config(spec)
            points_cm = build_eyelet_points(
                spec.output_width_cm,
                spec.output_height_cm,
                render.scaled_margin_cm,
                render.scaled_spacing_cm,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Błąd", str(exc))
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz PDF z oczkami",
            os.path.splitext(self.pdf_path)[0] + "_oczka.pdf",
            "PDF Files (*.pdf)",
        )
        if not save_path:
            return

        try:
            src_doc = fitz.open(self.pdf_path)
            base_output_width_pt = cm_to_pt(spec.output_width_cm)
            base_output_height_pt = cm_to_pt(spec.output_height_cm)
            input_width_pt = cm_to_pt(spec.input_width_cm)
            input_height_pt = cm_to_pt(spec.input_height_cm)
            wrap_margin_pt = cm_to_pt(render.scaled_wrap_cm)
            final_output_width_pt = cm_to_pt(render.final_width_cm)
            final_output_height_pt = cm_to_pt(render.final_height_cm)

            dst_doc = fitz.open()
            dst_page = dst_doc.new_page(width=final_output_width_pt, height=final_output_height_pt)

            base_left = wrap_margin_pt
            base_top = wrap_margin_pt
            base_right = base_left + base_output_width_pt
            base_bottom = base_top + base_output_height_pt

            offset_x = base_left + (base_output_width_pt - input_width_pt) / 2.0
            offset_y = base_top + (base_output_height_pt - input_height_pt) / 2.0
            target_rect = fitz.Rect(
                offset_x,
                offset_y,
                offset_x + input_width_pt,
                offset_y + input_height_pt,
            )
            dst_page.show_pdf_page(target_rect, src_doc, 0, keep_proportion=False, overlay=False)

            frame_base_width_pt = self.settings.get("frame_base_width_pt", DEFAULT_SETTINGS["frame_base_width_pt"])
            if self.border_checkbox.isChecked() or self.wrap_checkbox.isChecked():
                inner_rect = fitz.Rect(base_left, base_top, base_right, base_bottom)
                draw_frame(dst_page, inner_rect, frame_base_width_pt)
                if self.wrap_checkbox.isChecked():
                    outer_rect = fitz.Rect(0, 0, final_output_width_pt, final_output_height_pt)
                    draw_frame(dst_page, outer_rect, frame_base_width_pt)

            marker_pt = cm_to_pt(render.scaled_marker_size_cm)
            cross_outline_multiplier = self.settings.get("cross_outline_multiplier", DEFAULT_SETTINGS["cross_outline_multiplier"])
            cross_inner_multiplier = self.settings.get("cross_inner_multiplier", DEFAULT_SETTINGS["cross_inner_multiplier"])
            for x_cm, y_cm in points_cm:
                x_pt = base_left + cm_to_pt(x_cm)
                y_pt = base_top + base_output_height_pt - cm_to_pt(y_cm)
                draw_cross(dst_page, x_pt, y_pt, marker_pt, cross_outline_multiplier, cross_inner_multiplier)

            dst_doc.save(save_path)
            dst_doc.close()
            src_doc.close()
        except Exception as exc:
            QMessageBox.critical(self, "Błąd", f"Nie udało się zapisać PDF:\n{exc}")
            return

        QMessageBox.information(self, "Gotowe", f"Zapisano plik:\n{save_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
