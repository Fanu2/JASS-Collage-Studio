#!/usr/bin/env python3
"""
JASS Collage Studio v1.1
Photo collage editor with movable, scalable, rotatable image objects.

Install:
    python -m pip install PySide6

Run:
    python jass_collage_studio_v1_1.py
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import (
    QAction, QColor, QFont, QIcon, QImage, QPainter, QPen,
    QBrush, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox, QGraphicsDropShadowEffect,
    QToolBar, QStatusBar, QSplitter, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QSlider, QColorDialog, QInputDialog,
    QComboBox,
    QVBoxLayout, QHBoxLayout, QGroupBox, QFrame, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsTextItem
)

APP_NAME = "JASS Collage Studio"
VERSION = "1.3.3"


class ImageItem(QGraphicsPixmapItem):
    def __init__(self, pixmap, path):
        super().__init__(pixmap)
        self.path = path
        self.locked = False
        self.frame_width = 0
        self.frame_color = QColor("#ffffff")
        self.setToolTip(path)
        self.setFlags(
            QGraphicsPixmapItem.ItemIsMovable |
            QGraphicsPixmapItem.ItemIsSelectable |
            QGraphicsPixmapItem.ItemSendsGeometryChanges
        )
        self.setTransformationMode(Qt.SmoothTransformation)

    def set_locked(self, locked):
        self.locked = locked
        self.setFlag(
            QGraphicsPixmapItem.ItemIsMovable,
            not locked
        )
        self.setFlag(
            QGraphicsPixmapItem.ItemIsSelectable,
            True
        )

    def set_shadow(self, enabled):
        if enabled:
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(22)
            effect.setOffset(6, 6)
            effect.setColor(QColor(0, 0, 0, 150))
            self.setGraphicsEffect(effect)
        else:
            self.setGraphicsEffect(None)

    def set_frame(self, width, color):
        self.frame_width = width
        self.frame_color = color
        pen = QPen(color, width)
        self.setPen(pen)

    def itemChange(self, change, value):
        return super().itemChange(change, value)


class TextItem(QGraphicsTextItem):
    def __init__(self, text):
        super().__init__(text)
        self.setDefaultTextColor(QColor("white"))
        self.setFont(QFont("Segoe UI", 30, QFont.Bold))
        self.locked = False

    def set_locked(self, locked):
        self.locked = locked
        self.setFlag(
            QGraphicsTextItem.ItemIsMovable,
            not locked
        )
        self.setFlags(
            QGraphicsTextItem.ItemIsMovable |
            QGraphicsTextItem.ItemIsSelectable
        )


class Canvas(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setSceneRect(0, 0, 1200, 900)
        self.setRenderHints(
            QPainter.Antialiasing | QPainter.SmoothPixmapTransform
        )
        self.setAcceptDrops(True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.background = QColor("#f4f4f6")
        self.setBackgroundBrush(self.background)
        self._zoom = 1.0

    def add_image(self, path):
        pm = QPixmap(path)
        if pm.isNull():
            return None
        pm = pm.scaled(520, 520, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        item = ImageItem(pm, path)
        n = len(self.image_items())
        item.setPos(70 + (n % 4) * 60, 70 + (n % 4) * 60)
        self.scene.addItem(item)
        self.select(item)
        return item

    def add_images(self, paths):
        return [x for x in (self.add_image(p) for p in paths) if x]

    def image_items(self):
        return [
            x for x in self.scene.items()
            if isinstance(x, ImageItem)
        ]

    def selected(self):
        items = self.scene.selectedItems()
        return items[0] if items else None

    def select(self, item):
        self.scene.clearSelection()
        if item:
            item.setSelected(True)
            self.centerOn(item)

    def delete_selected(self):
        item = self.selected()
        if item:
            self.scene.removeItem(item)
            return item
        return None

    def duplicate_selected(self):
        item = self.selected()
        if not isinstance(item, ImageItem):
            return None
        new = ImageItem(item.pixmap(), item.path)
        new.setPos(item.pos() + self.scene.views()[0].mapToScene(20, 20)
                   - self.scene.views()[0].mapToScene(0, 0))
        new.setScale(item.scale())
        new.setRotation(item.rotation())
        new.setZValue(item.zValue() + 0.1)
        self.scene.addItem(new)
        self.select(new)
        return new

    def rotate(self, degrees):
        item = self.selected()
        if item:
            item.setRotation(item.rotation() + degrees)

    def scale_selected(self, percent):
        item = self.selected()
        if item:
            item.setScale(percent / 100.0)

    def bring_forward(self):
        item = self.selected()
        if item:
            item.setZValue(item.zValue() + 1)

    def send_backward(self):
        item = self.selected()
        if item:
            item.setZValue(item.zValue() - 1)

    def fit_selected(self):
        item = self.selected()
        if not item:
            return
        r = item.sceneBoundingRect()
        target = self.scene.sceneRect().adjusted(50, 50, -50, -50)
        if r.width() <= 0 or r.height() <= 0:
            return
        scale = min(target.width() / r.width(), target.height() / r.height())
        item.setScale(item.scale() * scale)
        item.setPos(
            target.center().x() - item.boundingRect().width() * item.scale() / 2,
            target.center().y() - item.boundingRect().height() * item.scale() / 2
        )

    def template_grid(self, columns, rows):
        items = self.image_items()
        if not items:
            return
        canvas = self.scene.sceneRect()
        margin, gap = 35, 18
        cw = (canvas.width() - 2*margin - gap*(columns-1)) / columns
        ch = (canvas.height() - 2*margin - gap*(rows-1)) / rows
        for i, item in enumerate(items[:columns*rows]):
            row, col = divmod(i, columns)
            x = margin + col*(cw+gap)
            y = margin + row*(ch+gap)
            bw = item.pixmap().width()
            bh = item.pixmap().height()
            scale = min(cw/bw, ch/bh)
            item.setScale(scale)
            item.setRotation(0)
            item.setPos(
                x + (cw-bw*scale)/2,
                y + (ch-bh*scale)/2
            )

    def zoom_in(self):
        self.scale(1.15, 1.15)
        self._zoom *= 1.15

    def zoom_out(self):
        self.scale(1/1.15, 1/1.15)
        self._zoom /= 1.15

    def zoom_reset(self):
        self.resetTransform()
        self._zoom = 1.0

    def add_text(self, text):
        if not text.strip():
            return
        item = TextItem(text)
        item.setPos(420, 390)
        self.scene.addItem(item)
        self.select(item)

    def add_rectangle(self):
        from PySide6.QtWidgets import QGraphicsRectItem
        item = QGraphicsRectItem(0, 0, 260, 160)
        item.setBrush(QBrush(QColor("#ffffff")))
        item.setPen(QPen(QColor("#ffffff"), 2))
        item.setFlags(
            QGraphicsRectItem.ItemIsMovable |
            QGraphicsRectItem.ItemIsSelectable
        )
        item.setPos(420, 300)
        self.scene.addItem(item)
        self.select(item)

    def add_circle(self):
        from PySide6.QtWidgets import QGraphicsEllipseItem
        item = QGraphicsEllipseItem(0, 0, 180, 180)
        item.setBrush(QBrush(QColor("#ff5f7a")))
        item.setPen(QPen(QColor("#ffffff"), 2))
        item.setFlags(
            QGraphicsEllipseItem.ItemIsMovable |
            QGraphicsEllipseItem.ItemIsSelectable
        )
        item.setPos(480, 330)
        self.scene.addItem(item)
        self.select(item)

    def export_image(self, filename, width=2000, height=1500):
        source = self.scene.sceneRect()
        image = QImage(width, height, QImage.Format_ARGB32)
        image.fill(self.background)
        painter = QPainter(image)
        painter.setRenderHints(
            QPainter.Antialiasing | QPainter.SmoothPixmapTransform
        )
        self.scene.render(painter, QRectF(0, 0, width, height), source)
        painter.end()
        image.save(filename)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p.lower().endswith(
                (".jpg",".jpeg",".png",".webp",".bmp",".gif",".tif",".tiff")
            ):
                paths.append(p)
        self.add_images(paths)
        event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.resize(1450, 900)
        self.setMinimumSize(1100, 720)
        self.build_ui()
        self.apply_theme()

    def build_ui(self):
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)

        def act(label, fn):
            a = QAction(label, self)
            a.triggered.connect(fn)
            tb.addAction(a)

        act("＋ Photos", self.open_images)
        act("＋ Text", self.add_text)
        act("▭ Rectangle", self.canvas_add_rectangle)
        act("● Circle", self.canvas_add_circle)
        tb.addSeparator()
        act("⟲ Rotate Left", lambda: self.rotate(-90))
        act("⟳ Rotate Right", lambda: self.rotate(90))
        act("Duplicate", self.duplicate)
        act("Delete", self.delete_selected)
        tb.addSeparator()
        act("Export", self.export)

        splitter = QSplitter(Qt.Horizontal)

        # LEFT
        left = QFrame()
        left.setMinimumWidth(250)
        left.setMaximumWidth(320)
        ll = QVBoxLayout(left)

        title = QLabel("JASS Collage Studio")
        title.setObjectName("title")
        ll.addWidget(title)

        sub = QLabel("Creative Design Studio • v1.3.3")
        sub.setObjectName("muted")
        ll.addWidget(sub)

        add = QPushButton("＋  Add Photos")
        add.clicked.connect(self.open_images)
        ll.addWidget(add)

        self.photo_list = QListWidget()
        self.photo_list.setIconSize(QSize(64, 64))
        self.photo_list.itemClicked.connect(self.select_from_list)
        ll.addWidget(self.photo_list, 1)

        rm = QPushButton("Remove Selected")
        rm.clicked.connect(self.delete_selected)
        ll.addWidget(rm)

        splitter.addWidget(left)

        # CENTER
        center = QFrame()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(8, 8, 8, 8)

        self.canvas = Canvas()
        cl.addWidget(self.canvas, 1)

        zr = QHBoxLayout()
        zr.addStretch()
        zo = QPushButton("−")
        zi = QPushButton("+")
        zreset = QPushButton("100%")
        zo.clicked.connect(self.canvas.zoom_out)
        zi.clicked.connect(self.canvas.zoom_in)
        zreset.clicked.connect(self.canvas.zoom_reset)
        zr.addWidget(zo)
        zr.addWidget(zreset)
        zr.addWidget(zi)
        cl.addLayout(zr)

        splitter.addWidget(center)

        # RIGHT
        right = QFrame()
        right.setMinimumWidth(270)
        right.setMaximumWidth(330)
        rl = QVBoxLayout(right)

        templates = QGroupBox("Templates")
        tl = QVBoxLayout(templates)
        for label, fn in [
            ("2 Photos", lambda: self.canvas.template_grid(2,1)),
            ("4 Photos", lambda: self.canvas.template_grid(2,2)),
            ("6 Photos", lambda: self.canvas.template_grid(3,2)),
            ("9 Photos", lambda: self.canvas.template_grid(3,3)),
        ]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            tl.addWidget(b)
        rl.addWidget(templates)

        edit = QGroupBox("Selected Photo")
        el = QVBoxLayout(edit)

        self.scale_label = QLabel("Scale: 100%")
        el.addWidget(self.scale_label)

        self.scale = QSlider(Qt.Horizontal)
        self.scale.setRange(10, 300)
        self.scale.setValue(100)
        self.scale.valueChanged.connect(self.change_scale)
        el.addWidget(self.scale)

        rr = QHBoxLayout()
        lrot = QPushButton("↺")
        rrot = QPushButton("↻")
        lrot.setToolTip("Rotate left")
        rrot.setToolTip("Rotate right")
        lrot.clicked.connect(lambda: self.rotate(-90))
        rrot.clicked.connect(lambda: self.rotate(90))
        rr.addWidget(lrot)
        rr.addWidget(rrot)
        el.addLayout(rr)

        fit = QPushButton("Fit to Canvas")
        fit.clicked.connect(self.canvas.fit_selected)
        el.addWidget(fit)

        dup = QPushButton("Duplicate")
        dup.clicked.connect(self.duplicate)
        el.addWidget(dup)

        layers = QHBoxLayout()
        front = QPushButton("Bring Forward")
        back = QPushButton("Send Back")
        front.clicked.connect(self.canvas.bring_forward)
        back.clicked.connect(self.canvas.send_backward)
        layers.addWidget(front)
        layers.addWidget(back)
        el.addLayout(layers)

        delete = QPushButton("🗑 Delete")
        delete.clicked.connect(self.delete_selected)
        el.addWidget(delete)

        rl.addWidget(edit)

        bg = QGroupBox("Background")
        bgl = QVBoxLayout(bg)

        color = QPushButton("Choose Color")
        color.clicked.connect(self.choose_background)
        bgl.addWidget(color)

        for label, c1, c2 in [
            ("Sunset", "#ff9966", "#ff5e62"),
            ("Ocean", "#2193b0", "#6dd5ed"),
            ("Purple", "#654ea3", "#eaafc8"),
        ]:
            b = QPushButton(label)
            b.clicked.connect(
                lambda checked=False, a=c1, b=c2: self.gradient(a, b)
            )
            bgl.addWidget(b)

        rl.addWidget(bg)

        design = QGroupBox("Design")
        dl = QVBoxLayout(design)

        lock = QPushButton("🔒 Lock / Unlock")
        lock.clicked.connect(self.toggle_lock)
        dl.addWidget(lock)

        shadow = QPushButton("✨ Toggle Photo Shadow")
        shadow.clicked.connect(self.toggle_shadow)
        dl.addWidget(shadow)

        frame = QPushButton("▣ White Photo Frame")
        frame.clicked.connect(lambda: self.apply_frame())
        dl.addWidget(frame)

        align_row1 = QHBoxLayout()
        for label, fn in [
            ("←", self.align_left),
            ("↔", self.snap_center),
            ("→", self.align_right),
        ]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            align_row1.addWidget(b)
        dl.addLayout(align_row1)

        align_row2 = QHBoxLayout()
        for label, fn in [
            ("↑", self.align_top),
            ("↕", self.snap_center),
            ("↓", self.align_bottom),
        ]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            align_row2.addWidget(b)
        dl.addLayout(align_row2)

        rl.addWidget(design)

        textbox = QGroupBox("Text Style")
        tx = QVBoxLayout(textbox)

        self.font_combo = QComboBox()
        self.font_combo.addItems([
            "Segoe UI", "Arial", "Georgia", "Times New Roman",
            "Courier New", "Verdana"
        ])
        self.font_combo.currentTextChanged.connect(self.change_font)
        tx.addWidget(self.font_combo)

        self.font_size = QSlider(Qt.Horizontal)
        self.font_size.setRange(10, 96)
        self.font_size.setValue(30)
        self.font_size.valueChanged.connect(self.change_font_size)
        tx.addWidget(self.font_size)

        self.bold_button = QPushButton("Bold")
        self.bold_button.setCheckable(True)
        self.bold_button.clicked.connect(self.change_bold)
        tx.addWidget(self.bold_button)

        text_color = QPushButton("Text Color")
        text_color.clicked.connect(self.choose_text_color)
        tx.addWidget(text_color)

        rl.addWidget(textbox)
        rl.addStretch()

        export = QPushButton("💾  Export Collage")
        export.setMinimumHeight(48)
        export.clicked.connect(self.export)
        rl.addWidget(export)

        splitter.addWidget(right)
        splitter.setSizes([280, 850, 310])

        self.setCentralWidget(splitter)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            "Ready — drag photos onto the canvas or use Add Photos"
        )

    def apply_theme(self):
        self.setStyleSheet("""
        QMainWindow { background:#101218; }
        QWidget { color:#e8ebf0; }
        QToolBar {
            background:#171a21; border-bottom:1px solid #303641;
            padding:6px; spacing:5px;
        }
        QToolButton {
            color:#f2f4f7;
            background:#252b35;
            border-radius:7px;
            padding:7px 10px;
        }
        QToolButton:hover {
            color:#ffffff;
            background:#343c49;
        }
        QPushButton {
            color:#f2f4f7;
            background:#252b35;
            border:1px solid #3b4350;
            border-radius:8px;
            padding:8px;
            font-size:13px;
        }
        QPushButton:hover {
            color:#ffffff;
            background:#333b49;
        }
        QPushButton:pressed {
            color:#ffffff;
            background:#1d222b;
        }
        QPushButton:disabled {
            color:#7f8794;
            background:#20252d;
        }
        QGroupBox {
            border:1px solid #303641; border-radius:10px;
            margin-top:12px; padding:10px;
        }
        QGroupBox::title {
            subcontrol-origin:margin; left:10px; padding:0 5px;
        }
        QListWidget {
            background:#171a20; border:1px solid #303641;
            border-radius:9px;
        }
        QListWidget::item { padding:7px; border-radius:6px; }
        QListWidget::item:selected { background:#344052; }
        QLabel#title { font-size:22px; font-weight:bold; }
        QLabel#muted { color:#9ca5b3; }
        QStatusBar { background:#171a20; color:#9ca5b3; }
        QComboBox {
            color:#f2f4f7;
            background:#252b35;
            border:1px solid #3b4350;
            border-radius:7px;
            padding:5px 8px;
        }
        QComboBox QAbstractItemView {
            color:#f2f4f7;
            background:#20252d;
            selection-background-color:#3b4b63;
        }

        QSlider::groove:horizontal {
            height:5px; background:#353d49; border-radius:3px;
        }
        QSlider::handle:horizontal {
            width:15px; margin:-5px 0; border-radius:8px;
            background:#8ab4ff;
        }
        """)

    def open_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Photos", "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp *.gif *.tif *.tiff)"
        )
        if not files:
            return
        items = self.canvas.add_images(files)
        for path, graphics_item in zip(files, items):
            li = QListWidgetItem(Path(path).name)
            pm = QPixmap(path).scaled(
                64,64,Qt.KeepAspectRatio,Qt.SmoothTransformation
            )
            li.setIcon(QIcon(pm))
            li.setData(Qt.UserRole, graphics_item)
            self.photo_list.addItem(li)
        self.statusBar().showMessage(f"Added {len(items)} photo(s)")

    def select_from_list(self, item):
        obj = item.data(Qt.UserRole)
        self.canvas.select(obj)
        self.sync_scale()

    def selected_image(self):
        item = self.canvas.selected()
        return item if isinstance(item, ImageItem) else None

    def sync_scale(self):
        item = self.selected_image()
        if item:
            value = max(10, min(300, round(item.scale()*100)))
            self.scale.blockSignals(True)
            self.scale.setValue(value)
            self.scale.blockSignals(False)
            self.scale_label.setText(f"Scale: {value}%")

    def change_scale(self, value):
        self.scale_label.setText(f"Scale: {value}%")
        self.canvas.scale_selected(value)

    def rotate(self, degrees):
        self.canvas.rotate(degrees)
        self.sync_scale()

    def duplicate(self):
        new = self.canvas.duplicate_selected()
        if new:
            li = QListWidgetItem(Path(new.path).name + " copy")
            li.setIcon(QIcon(new.pixmap().scaled(
                64,64,Qt.KeepAspectRatio,Qt.SmoothTransformation
            )))
            li.setData(Qt.UserRole, new)
            self.photo_list.addItem(li)
            self.photo_list.setCurrentItem(li)
            self.statusBar().showMessage("Photo duplicated")

    def delete_selected(self):
        selected = self.canvas.selected()
        if not selected:
            return
        for i in range(self.photo_list.count()-1, -1, -1):
            item = self.photo_list.item(i)
            if item.data(Qt.UserRole) is selected:
                self.photo_list.takeItem(i)
                break
        self.canvas.delete_selected()
        self.statusBar().showMessage("Selected item deleted")

    def add_text(self):
        text, ok = QInputDialog.getText(self, "Add Text", "Enter text:")
        if ok and text.strip():
            self.canvas.add_text(text)

    def canvas_add_rectangle(self):
        self.canvas.add_rectangle()

    def canvas_add_circle(self):
        self.canvas.add_circle()

    def choose_background(self):
        c = QColorDialog.getColor(
            self.canvas.background, self, "Choose Background"
        )
        if c.isValid():
            self.canvas.background = c
            self.canvas.setBackgroundBrush(c)

    def gradient(self, a, b):
        from PySide6.QtGui import QLinearGradient
        g = QLinearGradient(0,0,self.canvas.scene.width(),
                            self.canvas.scene.height())
        g.setColorAt(0, QColor(a))
        g.setColorAt(1, QColor(b))
        self.canvas.setBackgroundBrush(QBrush(g))

    def toggle_lock(self):
        state = self.canvas.toggle_lock_selected()
        if state is not None:
            self.statusBar().showMessage(
                "Selected object locked" if state else "Selected object unlocked"
            )

    def toggle_shadow(self):
        item = self.canvas.selected()
        if isinstance(item, ImageItem):
            enabled = item.graphicsEffect() is None
            item.set_shadow(enabled)
            self.statusBar().showMessage(
                "Photo shadow enabled" if enabled else "Photo shadow removed"
            )

    def apply_frame(self):
        item = self.canvas.selected()
        if isinstance(item, ImageItem):
            item.set_frame(8, QColor("#ffffff"))
            self.statusBar().showMessage("White photo frame applied")

    def align_left(self):
        self.canvas.align_left()

    def align_right(self):
        self.canvas.align_right()

    def align_top(self):
        self.canvas.align_top()

    def align_bottom(self):
        self.canvas.align_bottom()

    def snap_center(self):
        self.canvas.snap_selected()

    def change_font(self, family):
        self.canvas.style_selected_text(family=family)

    def change_font_size(self, value):
        self.canvas.style_selected_text(size=value)

    def change_bold(self, checked):
        self.canvas.style_selected_text(bold=checked)

    def choose_text_color(self):
        color = QColorDialog.getColor(QColor("white"), self, "Text Color")
        if color.isValid():
            self.canvas.style_selected_text(color=color)

    def export(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Collage", "my_collage.png",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg)"
        )
        if not filename:
            return
        try:
            self.canvas.export_image(filename, 2000, 1500)
            QMessageBox.information(
                self, "Export Complete",
                f"Collage exported successfully.\n\n{filename}"
            )
            self.statusBar().showMessage(f"Exported: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("JASS Digital Lab")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
