"""cat_loader.py - Módulo de carga y visualización de archivos CAD/PDF para ComCAD V1

Responsabilidades:
- Proveer funciones para seleccionar un archivo (DWG / PDF)
- Validar extensión
- Cargar DWG (usando ezdxf si está disponible) y extraer información básica (capas, entidades)
- Cargar PDF (usando PyMuPDF si está disponible; fallback a PyPDF2 para metadatos) y renderizar la primera página a QPixmap
- Entregar estructuras de datos simples que la UI (main.py) pueda consumir sin lógica de negocio adicional

Este módulo NO modifica widgets directamente: retorna datos y pixmaps para que la UI los integre.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Union

# Dependencias opcionales
try:
    import ezdxf  # type: ignore
except Exception:  # pragma: no cover
    ezdxf = None  # type: ignore

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None  # type: ignore

try:
    import PyPDF2  # type: ignore
except Exception:  # pragma: no cover
    PyPDF2 = None  # type: ignore

from PyQt5.QtWidgets import QFileDialog, QWidget
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

SUPPORTED_EXTENSIONS = {".dwg", ".pdf"}

# ===================== Data Structures ===================== #
@dataclass
class DwgLayerInfo:
    name: str
    color: Optional[int] = None
    frozen: Optional[bool] = None
    locked: Optional[bool] = None
    entity_count: int = 0

@dataclass
class DwgInfo:
    path: str
    layers: List[DwgLayerInfo] = field(default_factory=list)
    total_entities: int = 0
    model_space_entity_types: Dict[str, int] = field(default_factory=dict)
    extents: Optional[Tuple[float, float, float, float]] = None  # (xmin, ymin, xmax, ymax)
    library: str = "ezdxf"

@dataclass
class PdfPreview:
    path: str
    page_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    first_page_pixmap: Optional[QPixmap] = None
    library: str = "PyMuPDF|PyPDF2"

@dataclass
class LoadError:
    path: Optional[str]
    message: str
    detail: Optional[str] = None

@dataclass
class LoadResult:
    path: str
    type: str  # 'dwg' | 'pdf'
    dwg: Optional[DwgInfo] = None
    pdf: Optional[PdfPreview] = None
    error: Optional[LoadError] = None

    @property
    def ok(self) -> bool:
        return self.error is None

# ===================== Public API ===================== #

def abrir_archivo(parent: Optional[QWidget] = None, start_dir: Optional[str] = None) -> Optional[str]:
    """Abre un QFileDialog para seleccionar DWG o PDF y retorna la ruta o None si se canceló."""
    if start_dir is None:
        start_dir = os.path.expanduser("~")
    filtro = "Planos (*.dwg *.pdf);;DWG (*.dwg);;PDF (*.pdf);;Todos (*.*)"
    path, _ = QFileDialog.getOpenFileName(parent, "Abrir plano", start_dir, filtro)
    if not path:
        return None
    return path

def cargar_archivo(path: str, preview_pdf_max_px: int = 1600) -> LoadResult:
    """Carga un archivo DWG o PDF según su extensión y devuelve un LoadResult.

    :param path: Ruta al archivo.
    :param preview_pdf_max_px: Tamaño máximo (lado mayor) para el pixmap de la primera página del PDF.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return LoadResult(path=path, type="unknown", error=LoadError(path=path, message=f"Extensión no soportada: {ext}"))

    if ext == ".dwg":
        dwg_info = _cargar_dwg(path)
        if isinstance(dwg_info, LoadError):
            return LoadResult(path=path, type="dwg", error=dwg_info)
        return LoadResult(path=path, type="dwg", dwg=dwg_info)

    if ext == ".pdf":
        pdf_info = _cargar_pdf(path, preview_pdf_max_px=preview_pdf_max_px)
        if isinstance(pdf_info, LoadError):
            return LoadResult(path=path, type="pdf", error=pdf_info)
        return LoadResult(path=path, type="pdf", pdf=pdf_info)

    return LoadResult(path=path, type="unknown", error=LoadError(path=path, message="Tipo no manejado"))

# ===================== DWG ===================== #

def _cargar_dwg(path: str) -> Union[DwgInfo, LoadError]:
    if ezdxf is None:
        return LoadError(path=path, message="La librería ezdxf no está instalada.")

    if not os.path.isfile(path):
        return LoadError(path=path, message="Archivo no encontrado")

    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        layer_table = doc.layers

        layers_result: List[DwgLayerInfo] = []
        for layer in layer_table:
            try:
                ent_count = sum(1 for _ in msp.query(f"* [layer==\"{layer.dxf.name}\"]"))
            except Exception:
                ent_count = 0
            layers_result.append(
                DwgLayerInfo(
                    name=layer.dxf.name,
                    color=getattr(layer.dxf, "color", None),
                    frozen=getattr(layer.dxf, "is_frozen", None),
                    locked=getattr(layer.dxf, "is_locked", None),
                    entity_count=ent_count,
                )
            )

        # Conteo por tipo
        type_counts: Dict[str, int] = {}
        total_entities = 0
        for e in msp:
            t = e.dxftype()
            type_counts[t] = type_counts.get(t, 0) + 1
            total_entities += 1

        # Extents (puede fallar en algunos DWG)
        try:
            extents = doc.header.get("$EXTMIN"), doc.header.get("$EXTMAX")
            if extents[0] and extents[1]:
                (xmin, ymin, _zmin) = extents[0]
                (xmax, ymax, _zmax) = extents[1]
                bbox = (float(xmin), float(ymin), float(xmax), float(ymax))
            else:
                bbox = None
        except Exception:
            bbox = None

        return DwgInfo(
            path=path,
            layers=layers_result,
            total_entities=total_entities,
            model_space_entity_types=type_counts,
            extents=bbox,
        )
    except Exception as e:
        return LoadError(path=path, message="Error al cargar DWG", detail=str(e))

# ===================== PDF ===================== #

def _cargar_pdf(path: str, preview_pdf_max_px: int = 1600) -> Union[PdfPreview, LoadError]:
    if not os.path.isfile(path):
        return LoadError(path=path, message="Archivo no encontrado")

    # Intentar PyMuPDF primero para renderizar
    if fitz is not None:
        try:
            doc = fitz.open(path)
            meta = dict(doc.metadata or {})
            page_count = doc.page_count
            pixmap_qt: Optional[QPixmap] = None
            if page_count > 0:
                page = doc.load_page(0)
                # Escalar a resolución decente
                zoom = 1.0
                # Ajuste básico si la página es pequeña / grande
                rect = page.rect
                max_side = max(rect.width, rect.height)
                if max_side < 600:
                    zoom = 600 / max_side
                elif max_side > 2000:
                    zoom = 2000 / max_side
                mat = fitz.Matrix(zoom, zoom)
                pm = page.get_pixmap(alpha=False, matrix=mat)
                img = QImage(pm.samples, pm.width, pm.height, pm.stride, QImage.Format_RGB888)
                pixmap_qt = QPixmap.fromImage(img.copy())  # copy() para desacoplar del buffer original

                # Reducción adicional si excede preview_pdf_max_px
                if pixmap_qt and max(pixmap_qt.width(), pixmap_qt.height()) > preview_pdf_max_px:
                    pixmap_qt = pixmap_qt.scaled(preview_pdf_max_px, preview_pdf_max_px, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            doc.close()
            return PdfPreview(path=path, page_count=page_count, metadata=meta, first_page_pixmap=pixmap_qt, library="PyMuPDF")
        except Exception as e:
            # Caer a PyPDF2 si está disponible
            if PyPDF2 is None:
                return LoadError(path=path, message="Error al cargar PDF con PyMuPDF", detail=str(e))

    # PyMuPDF no disponible o falló -> usar PyPDF2 solo para metadatos (sin preview de imagen)
    if PyPDF2 is not None:
        try:
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                meta = dict(reader.metadata or {})
                page_count = len(reader.pages)
            return PdfPreview(path=path, page_count=page_count, metadata=meta, first_page_pixmap=None, library="PyPDF2")
        except Exception as e:
            return LoadError(path=path, message="Error al cargar PDF con PyPDF2", detail=str(e))

    return LoadError(path=path, message="No hay librerías disponibles para manejar PDF (instalar PyMuPDF o PyPDF2)")

# ===================== Helpers para UI ===================== #
def descripcion_corta(result: LoadResult) -> str:
    if not result.ok:
        return f"Error: {result.error.message if result.error else 'desconocido'}"
    if result.type == 'dwg' and result.dwg:
        return f"DWG: {len(result.dwg.layers)} capas, {result.dwg.total_entities} entidades"
    if result.type == 'pdf' and result.pdf:
        return f"PDF: {result.pdf.page_count} páginas"
    return os.path.basename(result.path)

def es_dwg(result: LoadResult) -> bool:
    return result.type == 'dwg' and result.dwg is not None and result.ok

def es_pdf(result: LoadResult) -> bool:
    return result.type == 'pdf' and result.pdf is not None and result.ok

# ===================== Ejemplo de integración (comentado) ===================== #
"""
Uso típico en main.py (pseudo-código):

from core import cat_loader

class VentanaPrincipal(QMainWindow):
    def _on_open(self):
        path = cat_loader.abrir_archivo(self)
        if not path:
            return
        result = cat_loader.cargar_archivo(path)
        if not result.ok:
            self.statusBar().showMessage(f"Error: {result.error.message}", 5000)
            return
        self.statusBar().showMessage(cat_loader.descripcion_corta(result), 4000)

        if cat_loader.es_pdf(result):
            pm = result.pdf.first_page_pixmap
            if pm:
                # Mostrar en una capa de previsualización o convertir a QGraphicsPixmapItem
                item = QGraphicsPixmapItem(pm)
                self.scene.addItem(item)

        elif cat_loader.es_dwg(result):
            # Podrías iterar entidades para crear representaciones simplificadas
            # (Placeholder) sólo mostrar bounding box si existe
            if result.dwg.extents:
                xmin, ymin, xmax, ymax = result.dwg.extents
                rect_item = QGraphicsRectItem(QRectF(xmin, ymin, xmax - xmin, ymax - ymin))
                rect_item.setPen(QPen(QColor('#4fc3f7'), 0))
                self.scene.addItem(rect_item)

"""

__all__ = [
    'abrir_archivo', 'cargar_archivo', 'descripcion_corta', 'es_dwg', 'es_pdf',
    'DwgInfo', 'PdfPreview', 'LoadResult', 'LoadError'
]