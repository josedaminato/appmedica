import * as XLSX from "xlsx"

export type ParsedSpreadsheet = {
  columns: string[]
  rows: Record<string, string>[]
}

const MAX_ROWS = 2000
const MAX_BYTES = 5 * 1024 * 1024

const ALLOWED_EXTENSIONS = [".xlsx", ".xlsm", ".xls", ".csv"]

export function validateImportFile(file: File): string | null {
  const name = file.name.toLowerCase()
  const okExt = ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext))
  if (!okExt) {
    return "Usá un archivo Excel (.xlsx) o CSV. En Excel: Archivo → Guardar como → Libro de Excel (.xlsx)."
  }
  if (file.size === 0) {
    return "El archivo está vacío."
  }
  if (file.size > MAX_BYTES) {
    return "El archivo supera 5 MB. Dividí la lista o eliminá filas vacías."
  }
  return null
}

/**
 * Lee el archivo en el navegador (permiso local del usuario).
 * No se sube el Excel al servidor hasta confirmar la importación.
 */
export async function readSpreadsheetFile(file: File): Promise<ParsedSpreadsheet> {
  const validationError = validateImportFile(file)
  if (validationError) {
    throw new Error(validationError)
  }

  let buffer: ArrayBuffer
  try {
    buffer = await file.arrayBuffer()
  } catch {
    throw new Error(
      "No pudimos abrir el archivo. Cerrá Excel si lo tenés abierto, guardá una copia en Descargas e intentá de nuevo.",
    )
  }

  let workbook: XLSX.WorkBook
  try {
    workbook = XLSX.read(buffer, {
      type: "array",
      cellDates: true,
      raw: false,
    })
  } catch {
    throw new Error(
      "Formato no reconocido. Guardá el archivo como .xlsx (Archivo → Guardar como) o exportá CSV.",
    )
  }

  const sheetName = workbook.SheetNames[0]
  if (!sheetName) {
    throw new Error("El archivo no tiene datos en la primera hoja.")
  }

  const sheet = workbook.Sheets[sheetName]
  const matrix = XLSX.utils.sheet_to_json<(string | number | null)[]>(sheet, {
    header: 1,
    defval: "",
    raw: false,
  }) as (string | number | null)[][]

  if (!matrix.length) {
    throw new Error("No hay filas en la planilla.")
  }

  let headerIndex = 0
  for (let i = 0; i < Math.min(matrix.length, 10); i++) {
    const cells = matrix[i].map(cellToString)
    if (cells.some((c) => c.length > 0)) {
      headerIndex = i
      break
    }
  }

  const headers = normalizeHeaders(matrix[headerIndex].map(cellToString))
  if (!headers.some((h) => h.length > 0)) {
    throw new Error("La primera fila con datos debe tener nombres de columnas (Nombre, Apellido, DNI…).")
  }

  const rows: Record<string, string>[] = []
  for (let i = headerIndex + 1; i < matrix.length && rows.length < MAX_ROWS; i++) {
    const cells = matrix[i].map(cellToString)
    if (!cells.some((c) => c.length > 0)) continue

    const row: Record<string, string> = {}
    headers.forEach((header, idx) => {
      if (!header) return
      row[header] = cells[idx] ?? ""
    })
    if (Object.values(row).some((v) => v.trim())) {
      rows.push(row)
    }
  }

  if (!rows.length) {
    throw new Error("No encontramos pacientes debajo de los encabezados.")
  }

  return { columns: headers.filter(Boolean), rows }
}

function cellToString(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return ""
  return String(value).trim()
}

function normalizeHeaders(cells: string[]): string[] {
  const seen: Record<string, number> = {}
  return cells.map((cell) => {
    const base = cell.trim() || "columna"
    const count = seen[base] ?? 0
    seen[base] = count + 1
    return count === 0 ? base : `${base}_${count + 1}`
  })
}
