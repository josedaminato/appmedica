import { Link } from "react-router-dom"

export function InsuranceCatalogHint() {
  return (
    <p className="text-xs text-muted-foreground">
      Todavía no cargaste obras sociales.{" "}
      <Link to="/insurances?tab=catalog" className="font-medium text-primary hover:underline">
        Agregá las que usás en tu consultorio
      </Link>
      .
    </p>
  )
}
