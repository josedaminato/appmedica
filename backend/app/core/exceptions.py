from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


def not_found(resource: str = "Recurso") -> AppException:
    return AppException(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"{resource} no encontrado")


def conflict(message: str) -> AppException:
    return AppException(status.HTTP_409_CONFLICT, "CONFLICT", message)


def unauthorized(message: str = "No autorizado") -> AppException:
    return AppException(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", message)


def bad_request(message: str) -> AppException:
    return AppException(status.HTTP_400_BAD_REQUEST, "BAD_REQUEST", message)
