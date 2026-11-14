/**
 * Helper compartido de exportación de reportes (Principio XI).
 *
 * `opcionesExportacion()` devuelve el menú de 3 formatos para cualquier
 * pantalla de reporte — CSV y Excel salen del MISMO arreglo de filas ya
 * cargado en el cliente (nunca un viaje nuevo al backend); PDF abre la vista
 * imprimible del propio componente (`imprimirPdf`, típicamente
 * `() => window.print()` con estilos `@media print`). Reportes de más de
 * ~5 000 filas solo ofrecen CSV (Excel/PDF con tanto detalle no son legibles
 * ni razonables de generar en el navegador).
 *
 * Usan este helper 013 y toda pantalla de listado exportable de 003-011 —
 * arreglar esta única implementación arregla la exportación en todas ellas.
 */

const FORMATOS_EXPORTACION = ['csv', 'excel', 'pdf']

function _filasDe(filas) {
  const f = typeof filas === 'function' ? filas() : filas
  return Array.isArray(f) ? f : []
}

function _descargarBlob(blob, nombreArchivo) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nombreArchivo
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

function _celdaCsv(valor) {
  if (valor === null || valor === undefined) return ''
  const s = typeof valor === 'object' ? JSON.stringify(valor) : String(valor)
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

function _filasACsv(filas) {
  if (!filas.length) return ''
  const columnas = Object.keys(filas[0])
  const filasTexto = filas.map((f) => columnas.map((c) => _celdaCsv(f[c])).join(','))
  return [columnas.map(_celdaCsv).join(','), ...filasTexto].join('\r\n')
}

function _descargarCsv(filas, nombreArchivo) {
  // BOM UTF-8 para que Excel abra tildes/eñes correctamente.
  const blob = new Blob(['﻿' + _filasACsv(filas)], { type: 'text/csv;charset=utf-8;' })
  _descargarBlob(blob, `${nombreArchivo}.csv`)
}

async function _descargarExcel(filas, nombreArchivo) {
  const XLSX = await import('xlsx')
  const hoja = XLSX.utils.json_to_sheet(filas)
  const libro = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(libro, hoja, 'Datos')
  XLSX.writeFile(libro, `${nombreArchivo}.xlsx`)
}

/**
 * @param {object} opciones
 * @param {(() => Array<object>) | Array<object>} [opciones.filas]  filas (o función que las devuelve) para CSV/Excel
 * @param {number} [opciones.totalFilas]          para decidir si se ofrece Excel/PDF (>5000 → solo CSV)
 * @param {() => void} [opciones.imprimirPdf]     abre la vista imprimible (PDF)
 * @param {string} [opciones.nombreArchivo]       nombre base del archivo descargado (sin extensión)
 * @returns {Array<{ formato: string, etiqueta: string, disponible: boolean, ejecutar: () => void }>}
 */
export function opcionesExportacion({ filas, totalFilas = 0, imprimirPdf, nombreArchivo = 'reporte' } = {}) {
  const soloCsv = totalFilas > 5000

  return [
    {
      formato: 'csv',
      etiqueta: 'Descargar CSV',
      disponible: true,
      ejecutar: () => _descargarCsv(_filasDe(filas), nombreArchivo),
    },
    {
      formato: 'excel',
      etiqueta: 'Descargar Excel',
      disponible: !soloCsv,
      ejecutar: () => _descargarExcel(_filasDe(filas), nombreArchivo),
    },
    {
      formato: 'pdf',
      etiqueta: 'Descargar PDF',
      disponible: !soloCsv,
      ejecutar: () => {
        if (typeof imprimirPdf === 'function') imprimirPdf()
      },
    },
  ]
}

export { FORMATOS_EXPORTACION }
