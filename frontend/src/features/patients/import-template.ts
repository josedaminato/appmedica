import * as XLSX from "xlsx"

/** Plantilla de ejemplo para descargar (una sola acción, sin permisos especiales). */
export function downloadPatientImportTemplate() {
  const rows = [
    ["Nombre", "Apellido", "DNI", "Teléfono", "Email", "Obra social", "Nº afiliado", "Notas"],
    ["María", "García", "30123456", "+5491155551234", "maria@email.com", "Swiss Medical", "123456", ""],
    ["Juan", "Pérez", "28999888", "", "", "OSDE", "", "Paciente habitual"],
  ]
  const sheet = XLSX.utils.aoa_to_sheet(rows)
  const book = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(book, sheet, "Pacientes")
  XLSX.writeFile(book, "appmedica-pacientes-plantilla.xlsx")
}
