#!/usr/bin/env python3
"""
JASS Collage Studio
A polished PySide6 desktop collage maker.

Requirements:
    pip install PySide6 Pillow

Run:
    python jass_collage_studio.py
"""
import sys, os, math
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QRectF, QPointF
from PySide6.QtGui import (
    QAction, QImage, QPainter, QPen, QBrush, QColor, QPixmap,
    QFont, QIcon, QLinearGradient
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QSlider,
    QSpinBox, QComboBox, QColorDialog, QToolBar, QStatusBar,
    QHBoxLayout, QVBoxLayout, QGridLayout, QFrame, QSplitter,
    QScrollArea, QGroupBox
)

try:
    from PIL import Image, ImageOps, ImageEnhance
except ImportError:
    Image = None


APP_NAME = "JASS Collage Studio"
VERSION = "1.0"


class CollageCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(700, 520)
        self.setAutoFillBackground(True)
        self.images = []
        self.layout_name = "2 × 2"
        self.bg = QColor("#f5f5f5")
        self.border = QColor("#ffffff")
        self.spacing = 12
        self.radius = 0
        self.fit_mode = "Crop"
        self._pixmaps = []

    def set_images(self, paths):
        self.images = paths[:]
        self._pixmaps = []
        for p in self.images:
            pm = QPixmap(p)
            if not pm.isNull():
                self._pixmaps.append(pm)
        self.update()

    def set_options(self, layout_name=None, spacing=None, bg=None,
                    border=None, radius=None, fit_mode=None):
        if layout_name is not None:
            self.layout_name = layout_name
        if spacing is not None:
            self.spacing = spacing
        if bg is not None:
            self.bg = bg
        if border is not None:
            self.border = border
        if radius is not None:
            self.radius = radius
        if fit_mode is not None:
            self.fit_mode = fit_mode
        self.update()

    def _grid(self, n):
        if self.layout_name == "1 × 1":
            return 1, 1
        if self.layout_name == "1 × 2":
            return 2, 1
        if self.layout_name == "2 × 1":
            return 1, 2
        if self.layout_name == "3 × 1":
            return 1, 3
        if self.layout_name == "1 × 3":
            return 3, 1
        if self.layout_name == "3 × 3":
            return 3, 3
        if self.layout_name == "4 × 4":
            return 4, 4
        return 2, 2

    def _rounded_rect_path(self, rect, radius):
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        return path

    def _draw_image(self, painter, pm, rect):
        if pm.isNull():
            return
        if self.fit_mode == "Fit":
            scaled = pm.scaled(
                int(rect.width()), int(rect.height()),
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x = rect.x() + (rect.width() - scaled.width()) / 2
            y = rect.y() + (rect.height() - scaled.height()) / 2
            target = QRectF(x, y, scaled.width(), scaled.height())
            painter.drawPixmap(target, scaled)
        else:
            src_ratio = pm.width() / max(1, pm.height())
            dst_ratio = rect.width() / max(1, rect.height())
            if src_ratio > dst_ratio:
                h = pm.height()
                w = int(h * dst_ratio)
                x = (pm.width() - w) // 2
                source = QRectF(x, 0, w, h)
            else:
                w = pm.width()
                h = int(w / dst_ratio)
                y = (pm.height() - h) // 2
                source = QRectF(0, y, w, h)
            painter.drawPixmap(rect, pm, source)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # checker-like neutral workspace background
        painter.fillRect(self.rect(), QColor("#20242b"))

        margin = 32
        canvas = QRectF(margin, margin,
                        self.width() - 2 * margin,
                        self.height() - 2 * margin)
        painter.fillRect(canvas, self.bg)

        cols, rows = self._grid(max(1, len(self._pixmaps)))
        gap = self.spacing
        cell_w = (canvas.width() - gap * (cols - 1)) / cols
        cell_h = (canvas.height() - gap * (rows - 1)) / rows

        for i, pm in enumerate(self._pixmaps[:cols * rows]):
            r, c = divmod(i, cols)
            rect = QRectF(
                canvas.x() + c * (cell_w + gap),
                canvas.y() + r * (cell_h + gap),
                cell_w, cell_h
            )
            painter.save()
            if self.radius > 0:
                path = self._rounded_rect_path(rect, self.radius)
                painter.setClipPath(path)
            painter.setBrush(QBrush(self.border))
            painter.fillRect(rect, self.border)
            inner = rect.adjusted(3, 3, -3, -3)
            if self.radius > 0:
                path2 = self._rounded_rect_path(inner, max(0, self.radius - 3))
                painter.setClipPath(path2)
            self._draw_image(painter, pm, inner)
            painter.restore()

        if not self._pixmaps:
            painter.setPen(QColor("#8b93a1"))
            painter.setFont(QFont("Segoe UI", 18))
            painter.drawText(canvas, Qt.AlignCenter,
                            "Add photos to start creating your collage")
        painter.end()

    def render_image(self, width=1600, height=1200):
        out = QImage(width, height, QImage.Format_ARGB32)
        out.fill(self.bg)
        painter = QPainter(out)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        cols, rows = self._grid(max(1, len(self._pixmaps)))
        gap = int(self.spacing * width / max(1, self.width()))
        gap = max(0, gap)
        cell_w = (width - gap * (cols - 1)) / cols
        cell_h = (height - gap * (rows - 1)) / rows

        for i, pm in enumerate(self._pixmaps[:cols * rows]):
            r, c = divmod(i, cols)
            rect = QRectF(c * (cell_w + gap), r * (cell_h + gap),
                          cell_w, cell_h)
            painter.fillRect(rect, self.border)
            inner = rect.adjusted(3, 3, -3, -3)
            self._draw_image(painter, pm, inner)
        painter.end()
        return out


class DropList(QListWidget):
    def __init__(self, on_add):
        super().__init__()
        self.on_add = on_add
        self.setAcceptDrops(True)
        self.setIconSize(QSize(72, 72))
        self.setSpacing(4)
        self.setStyleSheet("""
            QListWidget {
                background:#171a20; border:1px solid #303641;
                border-radius:10px; color:#e9edf3; padding:6px;
            }
            QListWidget::item { padding:6px; border-radius:7px; }
            QListWidget::item:selected { background:#303846; }
        """)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = []
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p.lower().endswith((".jpg",".jpeg",".png",".webp",".bmp",".gif",".tif",".tiff")):
                paths.append(p)
        if paths:
            self.on_add(paths)
        e.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.resize(1320, 820)
        self.setMinimumSize(1050, 700)
        self.paths = []

        self.build_ui()
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet("""
        QMainWindow, QWidget { background:#111318; color:#e8ebf0; }
        QGroupBox {
            border:1px solid #303641; border-radius:10px;
            margin-top:12px; padding:12px; font-weight:600;
        }
        QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 5px; }
        QPushButton {
            background:#252a33; border:1px solid #3a424e;
            border-radius:8px; padding:8px 12px;
        }
        QPushButton:hover { background:#303744; }
        QPushButton:pressed { background:#1d222a; }
        QComboBox, QSpinBox {
            background:#1b1f26; border:1px solid #363e49;
            border-radius:7px; padding:6px;
        }
        QSlider::groove:horizontal { height:5px; background:#343b46; border-radius:3px; }
        QSlider::handle:horizontal { width:15px; margin:-5px 0; border-radius:8px; background:#8ab4ff; }
        QLabel#title { font-size:20px; font-weight:700; }
        QLabel#muted { color:#9da6b4; }
        QToolBar { background:#171a20; border-bottom:1px solid #303641; spacing:5px; }
        QStatusBar { background:#171a20; color:#9da6b4; }
        """)

    def build_ui(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_add = QAction("＋ Add Photos", self)
        act_add.triggered.connect(self.add_files)
        toolbar.addAction(act_add)

        act_save = QAction("Export", self)
        act_save.triggered.connect(self.export)
        toolbar.addAction(act_save)

        toolbar.addSeparator()
        act_clear = QAction("Clear", self)
        act_clear.triggered.connect(self.clear)
        toolbar.addAction(act_clear)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(14)

        left = QFrame()
        left.setFixedWidth(300)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0,0,0,0)

        title = QLabel("JASS Collage Studio")
        title.setObjectName("title")
        left_layout.addWidget(title)

        sub = QLabel("Create beautiful photo collages")
        sub.setObjectName("muted")
        left_layout.addWidget(sub)

        add = QPushButton("＋  Add Photos")
        add.clicked.connect(self.add_files)
        left_layout.addWidget(add)

        self.list = DropList(self.add_paths)
        left_layout.addWidget(self.list, 1)

        row = QHBoxLayout()
        rem = QPushButton("Remove Selected")
        rem.clicked.connect(self.remove_selected)
        up = QPushButton("↑")
        up.setToolTip("Move selected image up")
        up.clicked.connect(lambda: self.move_item(-1))
        down = QPushButton("↓")
        down.setToolTip("Move selected image down")
        down.clicked.connect(lambda: self.move_item(1))
        row.addWidget(rem)
        row.addWidget(up)
        row.addWidget(down)
        left_layout.addLayout(row)

        options = QGroupBox("Collage")
        grid = QGridLayout(options)

        grid.addWidget(QLabel("Layout"), 0, 0)
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["1 × 1","1 × 2","2 × 1","2 × 2",
                                    "3 × 1","1 × 3","3 × 3","4 × 4"])
        self.layout_combo.setCurrentText("2 × 2")
        self.layout_combo.currentTextChanged.connect(self.refresh)
        grid.addWidget(self.layout_combo, 0, 1)

        grid.addWidget(QLabel("Fit"), 1, 0)
        self.fit_combo = QComboBox()
        self.fit_combo.addItems(["Crop", "Fit"])
        self.fit_combo.currentTextChanged.connect(self.refresh)
        grid.addWidget(self.fit_combo, 1, 1)

        grid.addWidget(QLabel("Spacing"), 2, 0)
        self.spacing = QSlider(Qt.Horizontal)
        self.spacing.setRange(0, 40)
        self.spacing.setValue(12)
        self.spacing.valueChanged.connect(self.refresh)
        grid.addWidget(self.spacing, 2, 1)

        grid.addWidget(QLabel("Corners"), 3, 0)
        self.corners = QSlider(Qt.Horizontal)
        self.corners.setRange(0, 40)
        self.corners.setValue(0)
        self.corners.valueChanged.connect(self.refresh)
        grid.addWidget(self.corners, 3, 1)

        bg = QPushButton("Background")
        bg.clicked.connect(self.choose_bg)
        grid.addWidget(bg, 4, 0, 1, 2)

        border = QPushButton("Border")
        border.clicked.connect(self.choose_border)
        grid.addWidget(border, 5, 0, 1, 2)

        left_layout.addWidget(options)

        root.addWidget(left)

        center = QFrame()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0,0,0,0)
        self.canvas = CollageCanvas()
        center_layout.addWidget(self.canvas, 1)
        root.addWidget(center, 1)

        right = QFrame()
        right.setFixedWidth(220)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0,0,0,0)

        info = QGroupBox("Project")
        il = QVBoxLayout(info)
        self.count_label = QLabel("0 photos")
        self.size_label = QLabel("Canvas: preview")
        self.format_label = QLabel("Export: PNG / JPG")
        for w in (self.count_label, self.size_label, self.format_label):
            w.setObjectName("muted")
            il.addWidget(w)
        right_layout.addWidget(info)

        helpbox = QGroupBox("Tips")
        hl = QVBoxLayout(helpbox)
        for s in [
            "• Drag photos into the list",
            "• Reorder photos with ↑ / ↓",
            "• Try Crop or Fit",
            "• Adjust spacing and corners",
            "• Export a high-resolution image"
        ]:
            lab = QLabel(s)
            lab.setWordWrap(True)
            hl.addWidget(lab)
        right_layout.addWidget(helpbox)
        right_layout.addStretch()

        export = QPushButton("Export Collage")
        export.setMinimumHeight(44)
        export.clicked.connect(self.export)
        right_layout.addWidget(export)

        root.addWidget(right)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready — add some photos")

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Choose Photos", "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp *.gif *.tif *.tiff)"
        )
        if files:
            self.add_paths(files)

    def add_paths(self, paths):
        added = 0
        for p in paths:
            if p not in self.paths and os.path.isfile(p):
                self.paths.append(p)
                item = QListWidgetItem(os.path.basename(p))
                item.setToolTip(p)
                item.setIcon(QIcon(QPixmap(p).scaled(
                    72,72,Qt.KeepAspectRatio,Qt.SmoothTransformation)))
                self.list.addItem(item)
                added += 1
        self.refresh()
        self.statusBar().showMessage(f"Added {added} photo(s)")

    def remove_selected(self):
        rows = sorted([i.row() for i in self.list.selectedIndexes()], reverse=True)
        for r in rows:
            self.list.takeItem(r)
            self.paths.pop(r)
        self.refresh()

    def move_item(self, delta):
        row = self.list.currentRow()
        new = row + delta
        if row < 0 or new < 0 or new >= self.list.count():
            return
        item = self.list.takeItem(row)
        path = self.paths.pop(row)
        self.list.insertItem(new, item)
        self.paths.insert(new, path)
        self.list.setCurrentRow(new)
        self.refresh()

    def refresh(self):
        self.canvas.set_images(self.paths)
        self.canvas.set_options(
            layout_name=self.layout_combo.currentText(),
            spacing=self.spacing.value(),
            radius=self.corners.value(),
            fit_mode=self.fit_combo.currentText()
        )
        self.count_label.setText(f"{len(self.paths)} photo(s)")
        self.statusBar().showMessage(
            f"{len(self.paths)} photo(s) • {self.layout_combo.currentText()} • {self.fit_combo.currentText()}"
        )

    def choose_bg(self):
        c = QColorDialog.getColor(self.canvas.bg, self, "Choose Background")
        if c.isValid():
            self.canvas.bg = c
            self.canvas.update()

    def choose_border(self):
        c = QColorDialog.getColor(self.canvas.border, self, "Choose Border")
        if c.isValid():
            self.canvas.border = c
            self.canvas.update()

    def clear(self):
        self.paths.clear()
        self.list.clear()
        self.refresh()

    def export(self):
        if not self.paths:
            QMessageBox.information(self, "Nothing to export",
                                    "Add at least one photo first.")
            return
        path, selected = QFileDialog.getSaveFileName(
            self, "Export Collage", "my_collage.png",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg)"
        )
        if not path:
            return
        try:
            img = self.canvas.render_image(2000, 1500)
            if path.lower().endswith((".jpg",".jpeg")):
                if img.format() != QImage.Format_RGB32:
                    converted = img.convertToFormat(QImage.Format_RGB32)
                    img = converted
                ok = img.save(path, "JPEG", 95)
            else:
                ok = img.save(path, "PNG")
            if ok:
                self.statusBar().showMessage(f"Exported: {path}")
                QMessageBox.information(self, "Export complete",
                                        f"Collage saved successfully.\n\n{path}")
            else:
                raise RuntimeError("Qt could not save the image.")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("JASS Digital Lab")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
