from typing import Any

from dataclasses import asdict, is_dataclass

from sqlalchemy import text

from app.infrastructure.persistence.base_repository import BaseRepository


class PersonaRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    def get_persona(self, id_persona: int) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_persona,
                tipo_persona,
                nombre,
                apellido,
                razon_social,
                fecha_nacimiento_constitucion,
                estado_persona,
                observaciones
            FROM persona
            WHERE id_persona = :id_persona
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(statement, {"id_persona": id_persona}).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_persona": row["id_persona"],
            "tipo_persona": row["tipo_persona"],
            "nombre": row["nombre"],
            "apellido": row["apellido"],
            "razon_social": row["razon_social"],
            "fecha_nacimiento": row["fecha_nacimiento_constitucion"],
            "estado_persona": row["estado_persona"],
            "observaciones": row["observaciones"],
        }

    def create_persona(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "uid_global": values["uid_global"],
            "version_registro": values["version_registro"],
            "tipo_persona": values["tipo_persona"],
            "nombre": values["nombre"],
            "apellido": values["apellido"],
            "razon_social": values["razon_social"],
            "fecha_nacimiento_constitucion": values["fecha_nacimiento"],
            "estado_persona": values["estado_persona"],
            "fecha_alta": values["created_at"],
            "observaciones": values["observaciones"],
            "created_at": values["created_at"],
            "updated_at": values["updated_at"],
            "id_instalacion_origen": values["id_instalacion_origen"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_alta": values["op_id_alta"],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            INSERT INTO persona (
                uid_global,
                version_registro,
                tipo_persona,
                nombre,
                apellido,
                razon_social,
                fecha_nacimiento_constitucion,
                estado_persona,
                fecha_alta,
                observaciones,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion
            )
            VALUES (
                :uid_global,
                :version_registro,
                :tipo_persona,
                :nombre,
                :apellido,
                :razon_social,
                :fecha_nacimiento_constitucion,
                :estado_persona,
                :fecha_alta,
                :observaciones,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion
            )
            RETURNING
                id_persona,
                uid_global,
                version_registro,
                estado_persona
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_persona": row["id_persona"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "estado_persona": row["estado_persona"],
            }
        except Exception:
            self.db.rollback()
            raise

    def persona_exists(self, id_persona: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM persona
            WHERE id_persona = :id_persona
              AND deleted_at IS NULL
            """
        )
        result = self.db.execute(statement, {"id_persona": id_persona}).scalar_one_or_none()
        return result is not None

    def rol_participacion_exists(self, id_rol_participacion: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM rol_participacion
            WHERE id_rol_participacion = :id_rol_participacion
              AND deleted_at IS NULL
              AND estado_rol = 'ACTIVO'
            """
        )
        result = self.db.execute(
            statement, {"id_rol_participacion": id_rol_participacion}
        ).scalar_one_or_none()
        return result is not None

    def get_rol_participacion(
        self, id_rol_participacion: int
    ) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT id_rol_participacion, estado_rol
            FROM rol_participacion
            WHERE id_rol_participacion = :id_rol_participacion
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_rol_participacion": id_rol_participacion}
        ).mappings().one_or_none()
        if row is None:
            return None
        return {
            "id_rol_participacion": row["id_rol_participacion"],
            "estado_rol": row["estado_rol"],
        }

    def relacion_objetivo_exists(self, tipo_relacion: str, id_relacion: int) -> bool:
        # Compatibilidad heredada: `relacion_persona_rol` valida el contexto
        # contra tablas de otros dominios porque la asociacion polimorfica ya
        # esta materializada en SQL y en la API vigente.
        table_map = {
            "venta": ("venta", "id_venta"),
            "contrato_alquiler": ("contrato_alquiler", "id_contrato_alquiler"),
            "cesion": ("cesion", "id_cesion"),
            "escrituracion": ("escrituracion", "id_escrituracion"),
            "reserva_venta": ("reserva_venta", "id_reserva_venta"),
            "reserva_locativa": ("reserva_locativa", "id_reserva_locativa"),
        }
        mapping = table_map.get(tipo_relacion)
        if mapping is None:
            return False

        table_name, pk_name = mapping
        statement = text(
            f"""
            SELECT 1
            FROM {table_name}
            WHERE {pk_name} = :id_relacion
            """
        )
        result = self.db.execute(statement, {"id_relacion": id_relacion}).scalar_one_or_none()
        return result is not None

    def get_persona_for_update(self, id_persona: int) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_persona,
                tipo_persona,
                nombre,
                apellido,
                razon_social,
                fecha_nacimiento_constitucion,
                estado_persona,
                observaciones,
                version_registro
            FROM persona
            WHERE id_persona = :id_persona
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(statement, {"id_persona": id_persona}).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_persona": row["id_persona"],
            "tipo_persona": row["tipo_persona"],
            "nombre": row["nombre"],
            "apellido": row["apellido"],
            "razon_social": row["razon_social"],
            "fecha_nacimiento": row["fecha_nacimiento_constitucion"],
            "estado_persona": row["estado_persona"],
            "observaciones": row["observaciones"],
            "version_registro": row["version_registro"],
        }

    def create_persona_documento(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "uid_global": values["uid_global"],
            "version_registro": values["version_registro"],
            "created_at": values["created_at"],
            "updated_at": values["updated_at"],
            "id_instalacion_origen": values["id_instalacion_origen"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_alta": values["op_id_alta"],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
            "id_persona": values["id_persona"],
            "tipo_documento_persona": values["tipo_documento"],
            "numero_documento": values["numero_documento"],
            "pais_emision": values["pais_emision"],
            "es_principal": values["es_principal"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "observaciones": values["observaciones"],
        }

        statement = text(
            """
            INSERT INTO persona_documento (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_persona,
                tipo_documento_persona,
                numero_documento,
                pais_emision,
                es_principal,
                fecha_desde,
                fecha_hasta,
                observaciones
            )
            VALUES (
                :uid_global,
                :version_registro,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_persona,
                :tipo_documento_persona,
                :numero_documento,
                :pais_emision,
                :es_principal,
                :fecha_desde,
                :fecha_hasta,
                :observaciones
            )
            RETURNING
                id_persona_documento,
                uid_global,
                version_registro,
                id_persona,
                tipo_documento_persona,
                numero_documento,
                es_principal
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_persona_documento": row["id_persona_documento"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "id_persona": row["id_persona"],
                "tipo_documento_persona": row["tipo_documento_persona"],
                "numero_documento": row["numero_documento"],
                "es_principal": row["es_principal"],
            }
        except Exception:
            self.db.rollback()
            raise

    def create_relacion_persona_rol(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "uid_global": values["uid_global"],
            "version_registro": values["version_registro"],
            "created_at": values["created_at"],
            "updated_at": values["updated_at"],
            "id_instalacion_origen": values["id_instalacion_origen"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_alta": values["op_id_alta"],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
            "id_persona": values["id_persona"],
            "id_rol_participacion": values["id_rol_participacion"],
            "tipo_relacion": values["tipo_relacion"],
            "id_relacion": values["id_relacion"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "observaciones": values["observaciones"],
        }

        statement = text(
            """
            INSERT INTO relacion_persona_rol (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_persona,
                id_rol_participacion,
                tipo_relacion,
                id_relacion,
                fecha_desde,
                fecha_hasta,
                observaciones
            )
            VALUES (
                :uid_global,
                :version_registro,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_persona,
                :id_rol_participacion,
                :tipo_relacion,
                :id_relacion,
                :fecha_desde,
                :fecha_hasta,
                :observaciones
            )
            RETURNING
                id_relacion_persona_rol,
                id_persona,
                id_rol_participacion,
                tipo_relacion,
                id_relacion,
                version_registro,
                fecha_desde,
                fecha_hasta
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_relacion_persona_rol": row["id_relacion_persona_rol"],
                "id_persona": row["id_persona"],
                "id_rol_participacion": row["id_rol_participacion"],
                "tipo_relacion": row["tipo_relacion"],
                "id_relacion": row["id_relacion"],
                "version_registro": row["version_registro"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
            }
        except Exception:
            self.db.rollback()
            raise

    def update_persona(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_persona": values["id_persona"],
            "tipo_persona": values["tipo_persona"],
            "nombre": values["nombre"],
            "apellido": values["apellido"],
            "razon_social": values["razon_social"],
            "fecha_nacimiento_constitucion": values["fecha_nacimiento"],
            "estado_persona": values["estado_persona"],
            "observaciones": values["observaciones"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE persona
            SET
                tipo_persona = :tipo_persona,
                nombre = :nombre,
                apellido = :apellido,
                razon_social = :razon_social,
                fecha_nacimiento_constitucion = :fecha_nacimiento_constitucion,
                estado_persona = :estado_persona,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_persona = :id_persona
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_persona,
                version_registro,
                tipo_persona,
                nombre,
                apellido,
                razon_social,
                estado_persona
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_persona": row["id_persona"],
                "version_registro": row["version_registro"],
                "tipo_persona": row["tipo_persona"],
                "nombre": row["nombre"],
                "apellido": row["apellido"],
                "razon_social": row["razon_social"],
                "estado_persona": row["estado_persona"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_persona(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_persona": values["id_persona"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "deleted_at": values["deleted_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE persona
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_persona = :id_persona
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_persona,
                version_registro
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_persona": row["id_persona"],
                "version_registro": row["version_registro"],
            }
        except Exception:
            self.db.rollback()
            raise

    def create_persona_domicilio(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "uid_global": values["uid_global"],
            "version_registro": values["version_registro"],
            "created_at": values["created_at"],
            "updated_at": values["updated_at"],
            "id_instalacion_origen": values["id_instalacion_origen"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_alta": values["op_id_alta"],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
            "id_persona": values["id_persona"],
            "tipo_domicilio": values["tipo_domicilio"],
            "direccion": values["direccion"],
            "localidad": values["localidad"],
            "provincia": values["provincia"],
            "pais": values["pais"],
            "codigo_postal": values["codigo_postal"],
            "es_principal": values["es_principal"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "observaciones": values["observaciones"],
        }

        statement = text(
            """
            INSERT INTO persona_domicilio (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_persona,
                tipo_domicilio,
                direccion,
                localidad,
                provincia,
                pais,
                codigo_postal,
                es_principal,
                fecha_desde,
                fecha_hasta,
                observaciones
            )
            VALUES (
                :uid_global,
                :version_registro,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_persona,
                :tipo_domicilio,
                :direccion,
                :localidad,
                :provincia,
                :pais,
                :codigo_postal,
                :es_principal,
                :fecha_desde,
                :fecha_hasta,
                :observaciones
            )
            RETURNING
                id_persona_domicilio,
                uid_global,
                version_registro,
                id_persona,
                tipo_domicilio,
                direccion,
                es_principal
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_persona_domicilio": row["id_persona_domicilio"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "id_persona": row["id_persona"],
                "tipo_domicilio": row["tipo_domicilio"],
                "direccion": row["direccion"],
                "es_principal": row["es_principal"],
            }
        except Exception:
            self.db.rollback()
            raise

    def create_persona_contacto(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "uid_global": values["uid_global"],
            "version_registro": values["version_registro"],
            "created_at": values["created_at"],
            "updated_at": values["updated_at"],
            "id_instalacion_origen": values["id_instalacion_origen"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_alta": values["op_id_alta"],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
            "id_persona": values["id_persona"],
            "tipo_contacto": values["tipo_contacto"],
            "valor_contacto": values["valor_contacto"],
            "es_principal": values["es_principal"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "observaciones": values["observaciones"],
        }

        statement = text(
            """
            INSERT INTO persona_contacto (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_persona,
                tipo_contacto,
                valor_contacto,
                es_principal,
                fecha_desde,
                fecha_hasta,
                observaciones
            )
            VALUES (
                :uid_global,
                :version_registro,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_persona,
                :tipo_contacto,
                :valor_contacto,
                :es_principal,
                :fecha_desde,
                :fecha_hasta,
                :observaciones
            )
            RETURNING
                id_persona_contacto,
                uid_global,
                version_registro,
                id_persona,
                tipo_contacto,
                valor_contacto,
                es_principal
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_persona_contacto": row["id_persona_contacto"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "id_persona": row["id_persona"],
                "tipo_contacto": row["tipo_contacto"],
                "valor_contacto": row["valor_contacto"],
                "es_principal": row["es_principal"],
            }
        except Exception:
            self.db.rollback()
            raise

    def create_persona_relacion(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "uid_global": values["uid_global"],
            "version_registro": values["version_registro"],
            "created_at": values["created_at"],
            "updated_at": values["updated_at"],
            "id_instalacion_origen": values["id_instalacion_origen"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_alta": values["op_id_alta"],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
            "id_persona_origen": values["id_persona_origen"],
            "id_persona_destino": values["id_persona_destino"],
            "tipo_relacion": values["tipo_relacion"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "observaciones": values["observaciones"],
        }

        statement = text(
            """
            INSERT INTO persona_relacion (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_persona_origen,
                id_persona_destino,
                tipo_relacion,
                fecha_desde,
                fecha_hasta,
                observaciones
            )
            VALUES (
                :uid_global,
                :version_registro,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_persona_origen,
                :id_persona_destino,
                :tipo_relacion,
                :fecha_desde,
                :fecha_hasta,
                :observaciones
            )
            RETURNING
                id_persona_relacion,
                uid_global,
                version_registro,
                id_persona_origen,
                id_persona_destino,
                tipo_relacion
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_persona_relacion": row["id_persona_relacion"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "id_persona_origen": row["id_persona_origen"],
                "id_persona_destino": row["id_persona_destino"],
                "tipo_relacion": row["tipo_relacion"],
            }
        except Exception:
            self.db.rollback()
            raise

    def create_representacion_poder(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "uid_global": values["uid_global"],
            "version_registro": values["version_registro"],
            "created_at": values["created_at"],
            "updated_at": values["updated_at"],
            "id_instalacion_origen": values["id_instalacion_origen"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_alta": values["op_id_alta"],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
            "id_persona_representado": values["id_persona_representado"],
            "id_persona_representante": values["id_persona_representante"],
            "tipo_poder": values["tipo_poder"],
            "estado_representacion": values["estado_representacion"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "descripcion": values["descripcion"],
        }

        statement = text(
            """
            INSERT INTO representacion_poder (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_persona_representado,
                id_persona_representante,
                tipo_poder,
                estado_representacion,
                fecha_desde,
                fecha_hasta,
                descripcion
            )
            VALUES (
                :uid_global,
                :version_registro,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_persona_representado,
                :id_persona_representante,
                :tipo_poder,
                :estado_representacion,
                :fecha_desde,
                :fecha_hasta,
                :descripcion
            )
            RETURNING
                id_representacion_poder,
                uid_global,
                version_registro,
                id_persona_representado,
                id_persona_representante,
                tipo_poder,
                estado_representacion
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_representacion_poder": row["id_representacion_poder"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "id_persona_representado": row["id_persona_representado"],
                "id_persona_representante": row["id_persona_representante"],
                "tipo_poder": row["tipo_poder"],
                "estado_representacion": row["estado_representacion"],
            }
        except Exception:
            self.db.rollback()
            raise

    def get_persona_contactos(self, id_persona: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_persona_contacto,
                tipo_contacto,
                valor_contacto,
                es_principal
            FROM persona_contacto
            WHERE id_persona = :id_persona
              AND deleted_at IS NULL
            ORDER BY id_persona_contacto
            """
        )
        result = self.db.execute(statement, {"id_persona": id_persona})
        rows = result.mappings().all()
        return [
            {
                "id_persona_contacto": row["id_persona_contacto"],
                "tipo_contacto": row["tipo_contacto"],
                "valor_contacto": row["valor_contacto"],
                "es_principal": row["es_principal"],
            }
            for row in rows
        ]

    def get_persona_relaciones(self, id_persona_origen: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_persona_relacion,
                id_persona_origen,
                id_persona_destino,
                tipo_relacion,
                fecha_desde,
                fecha_hasta
            FROM persona_relacion
            WHERE id_persona_origen = :id_persona_origen
              AND deleted_at IS NULL
            ORDER BY id_persona_relacion
            """
        )
        result = self.db.execute(statement, {"id_persona_origen": id_persona_origen})
        rows = result.mappings().all()
        return [
            {
                "id_persona_relacion": row["id_persona_relacion"],
                "id_persona_origen": row["id_persona_origen"],
                "id_persona_destino": row["id_persona_destino"],
                "tipo_relacion": row["tipo_relacion"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
            }
            for row in rows
        ]

    def get_representaciones_poder(
        self, id_persona_representado: int
    ) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_representacion_poder,
                id_persona_representado,
                id_persona_representante,
                tipo_poder,
                estado_representacion,
                fecha_desde,
                fecha_hasta
            FROM representacion_poder
            WHERE id_persona_representado = :id_persona_representado
              AND deleted_at IS NULL
            ORDER BY id_representacion_poder
            """
        )
        result = self.db.execute(
            statement, {"id_persona_representado": id_persona_representado}
        )
        rows = result.mappings().all()
        return [
            {
                "id_representacion_poder": row["id_representacion_poder"],
                "id_persona_representado": row["id_persona_representado"],
                "id_persona_representante": row["id_persona_representante"],
                "tipo_poder": row["tipo_poder"],
                "estado_representacion": row["estado_representacion"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
            }
            for row in rows
        ]

    def get_persona_domicilios(self, id_persona: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_persona_domicilio,
                tipo_domicilio,
                direccion,
                localidad,
                provincia,
                pais,
                codigo_postal,
                es_principal
            FROM persona_domicilio
            WHERE id_persona = :id_persona
              AND deleted_at IS NULL
            ORDER BY id_persona_domicilio
            """
        )
        result = self.db.execute(statement, {"id_persona": id_persona})
        rows = result.mappings().all()
        return [
            {
                "id_persona_domicilio": row["id_persona_domicilio"],
                "tipo_domicilio": row["tipo_domicilio"],
                "direccion": row["direccion"],
                "localidad": row["localidad"],
                "provincia": row["provincia"],
                "pais": row["pais"],
                "codigo_postal": row["codigo_postal"],
                "es_principal": row["es_principal"],
            }
            for row in rows
        ]

    def get_persona_documentos(self, id_persona: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_persona_documento,
                tipo_documento_persona,
                numero_documento,
                pais_emision,
                es_principal
            FROM persona_documento
            WHERE id_persona = :id_persona
              AND deleted_at IS NULL
            ORDER BY id_persona_documento
            """
        )
        result = self.db.execute(statement, {"id_persona": id_persona})
        rows = result.mappings().all()
        return [
            {
                "id_persona_documento": row["id_persona_documento"],
                "tipo_documento": row["tipo_documento_persona"],
                "numero_documento": row["numero_documento"],
                "pais_emision": row["pais_emision"],
                "es_principal": row["es_principal"],
            }
            for row in rows
        ]

    def get_persona_participaciones(self, id_persona: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_relacion_persona_rol,
                id_persona,
                id_rol_participacion,
                tipo_relacion,
                id_relacion,
                fecha_desde,
                fecha_hasta
            FROM relacion_persona_rol
            WHERE id_persona = :id_persona
              AND deleted_at IS NULL
            ORDER BY id_relacion_persona_rol
            """
        )
        result = self.db.execute(statement, {"id_persona": id_persona})
        rows = result.mappings().all()
        return [
            {
                "id_relacion_persona_rol": row["id_relacion_persona_rol"],
                "id_persona": row["id_persona"],
                "id_rol_participacion": row["id_rol_participacion"],
                "tipo_relacion": row["tipo_relacion"],
                "id_relacion": row["id_relacion"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
            }
            for row in rows
        ]

    def get_relacion_persona_rol_for_update(
        self, id_relacion_persona_rol: int
    ) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_relacion_persona_rol,
                id_persona,
                version_registro
            FROM relacion_persona_rol
            WHERE id_relacion_persona_rol = :id_relacion_persona_rol
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_relacion_persona_rol": id_relacion_persona_rol}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_relacion_persona_rol": row["id_relacion_persona_rol"],
            "id_persona": row["id_persona"],
            "version_registro": row["version_registro"],
        }

    def get_persona_contacto_for_update(
        self, id_persona_contacto: int
    ) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_persona_contacto,
                id_persona,
                version_registro
            FROM persona_contacto
            WHERE id_persona_contacto = :id_persona_contacto
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_persona_contacto": id_persona_contacto}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_persona_contacto": row["id_persona_contacto"],
            "id_persona": row["id_persona"],
            "version_registro": row["version_registro"],
        }

    def get_persona_relacion_for_update(
        self, id_persona_relacion: int
    ) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_persona_relacion,
                id_persona_origen,
                version_registro
            FROM persona_relacion
            WHERE id_persona_relacion = :id_persona_relacion
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_persona_relacion": id_persona_relacion}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_persona_relacion": row["id_persona_relacion"],
            "id_persona_origen": row["id_persona_origen"],
            "version_registro": row["version_registro"],
        }

    def get_representacion_poder_for_update(
        self, id_representacion_poder: int
    ) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_representacion_poder,
                id_persona_representado,
                version_registro
            FROM representacion_poder
            WHERE id_representacion_poder = :id_representacion_poder
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_representacion_poder": id_representacion_poder}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_representacion_poder": row["id_representacion_poder"],
            "id_persona_representado": row["id_persona_representado"],
            "version_registro": row["version_registro"],
        }

    def get_persona_documento_for_update(
        self, id_persona_documento: int
    ) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_persona_documento,
                id_persona,
                version_registro
            FROM persona_documento
            WHERE id_persona_documento = :id_persona_documento
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_persona_documento": id_persona_documento}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_persona_documento": row["id_persona_documento"],
            "id_persona": row["id_persona"],
            "version_registro": row["version_registro"],
        }

    def get_persona_domicilio_for_update(
        self, id_persona_domicilio: int
    ) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_persona_domicilio,
                id_persona,
                version_registro
            FROM persona_domicilio
            WHERE id_persona_domicilio = :id_persona_domicilio
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_persona_domicilio": id_persona_domicilio}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_persona_domicilio": row["id_persona_domicilio"],
            "id_persona": row["id_persona"],
            "version_registro": row["version_registro"],
        }

    def update_persona_contacto(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_persona_contacto": values["id_persona_contacto"],
            "tipo_contacto": values["tipo_contacto"],
            "valor_contacto": values["valor_contacto"],
            "es_principal": values["es_principal"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "observaciones": values["observaciones"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE persona_contacto
            SET
                tipo_contacto = :tipo_contacto,
                valor_contacto = :valor_contacto,
                es_principal = :es_principal,
                fecha_desde = :fecha_desde,
                fecha_hasta = :fecha_hasta,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_persona_contacto = :id_persona_contacto
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_persona_contacto,
                version_registro,
                id_persona,
                tipo_contacto,
                valor_contacto,
                es_principal
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_persona_contacto": row["id_persona_contacto"],
                "version_registro": row["version_registro"],
                "id_persona": row["id_persona"],
                "tipo_contacto": row["tipo_contacto"],
                "valor_contacto": row["valor_contacto"],
                "es_principal": row["es_principal"],
            }
        except Exception:
            self.db.rollback()
            raise

    def update_persona_relacion(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_persona_relacion": values["id_persona_relacion"],
            "id_persona_destino": values["id_persona_destino"],
            "tipo_relacion": values["tipo_relacion"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "observaciones": values["observaciones"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE persona_relacion
            SET
                id_persona_destino = :id_persona_destino,
                tipo_relacion = :tipo_relacion,
                fecha_desde = :fecha_desde,
                fecha_hasta = :fecha_hasta,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_persona_relacion = :id_persona_relacion
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_persona_relacion,
                id_persona_origen,
                id_persona_destino,
                tipo_relacion,
                version_registro,
                fecha_desde,
                fecha_hasta
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_persona_relacion": row["id_persona_relacion"],
                "id_persona_origen": row["id_persona_origen"],
                "id_persona_destino": row["id_persona_destino"],
                "tipo_relacion": row["tipo_relacion"],
                "version_registro": row["version_registro"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
            }
        except Exception:
            self.db.rollback()
            raise

    def update_representacion_poder(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_representacion_poder": values["id_representacion_poder"],
            "id_persona_representante": values["id_persona_representante"],
            "tipo_poder": values["tipo_poder"],
            "estado_representacion": values["estado_representacion"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "descripcion": values["descripcion"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE representacion_poder
            SET
                id_persona_representante = :id_persona_representante,
                tipo_poder = :tipo_poder,
                estado_representacion = :estado_representacion,
                fecha_desde = :fecha_desde,
                fecha_hasta = :fecha_hasta,
                descripcion = :descripcion,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_representacion_poder = :id_representacion_poder
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_representacion_poder,
                id_persona_representado,
                id_persona_representante,
                estado_representacion,
                tipo_poder,
                version_registro,
                fecha_desde,
                fecha_hasta
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_representacion_poder": row["id_representacion_poder"],
                "id_persona_representado": row["id_persona_representado"],
                "id_persona_representante": row["id_persona_representante"],
                "estado_representacion": row["estado_representacion"],
                "tipo_poder": row["tipo_poder"],
                "version_registro": row["version_registro"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_persona_contacto(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_persona_contacto": values["id_persona_contacto"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "deleted_at": values["deleted_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE persona_contacto
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_persona_contacto = :id_persona_contacto
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_persona_contacto,
                version_registro,
                id_persona
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_persona_contacto": row["id_persona_contacto"],
                "version_registro": row["version_registro"],
                "id_persona": row["id_persona"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_persona_relacion(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_persona_relacion": values["id_persona_relacion"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "deleted_at": values["deleted_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE persona_relacion
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_persona_relacion = :id_persona_relacion
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_persona_relacion,
                version_registro,
                id_persona_origen
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_persona_relacion": row["id_persona_relacion"],
                "version_registro": row["version_registro"],
                "id_persona_origen": row["id_persona_origen"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_representacion_poder(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_representacion_poder": values["id_representacion_poder"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "deleted_at": values["deleted_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE representacion_poder
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_representacion_poder = :id_representacion_poder
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_representacion_poder,
                version_registro,
                id_persona_representado
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_representacion_poder": row["id_representacion_poder"],
                "version_registro": row["version_registro"],
                "id_persona_representado": row["id_persona_representado"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_persona_domicilio(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_persona_domicilio": values["id_persona_domicilio"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "deleted_at": values["deleted_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE persona_domicilio
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_persona_domicilio = :id_persona_domicilio
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_persona_domicilio,
                version_registro,
                id_persona
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_persona_domicilio": row["id_persona_domicilio"],
                "version_registro": row["version_registro"],
                "id_persona": row["id_persona"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_persona_documento(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_persona_documento": values["id_persona_documento"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "deleted_at": values["deleted_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE persona_documento
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_persona_documento = :id_persona_documento
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_persona_documento,
                version_registro,
                id_persona
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_persona_documento": row["id_persona_documento"],
                "version_registro": row["version_registro"],
                "id_persona": row["id_persona"],
            }
        except Exception:
            self.db.rollback()
            raise

    def update_persona_documento(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_persona_documento": values["id_persona_documento"],
            "tipo_documento_persona": values["tipo_documento"],
            "numero_documento": values["numero_documento"],
            "pais_emision": values["pais_emision"],
            "es_principal": values["es_principal"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "observaciones": values["observaciones"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE persona_documento
            SET
                tipo_documento_persona = :tipo_documento_persona,
                numero_documento = :numero_documento,
                pais_emision = :pais_emision,
                es_principal = :es_principal,
                fecha_desde = :fecha_desde,
                fecha_hasta = :fecha_hasta,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_persona_documento = :id_persona_documento
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_persona_documento,
                version_registro,
                id_persona,
                tipo_documento_persona,
                numero_documento,
                pais_emision,
                es_principal
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_persona_documento": row["id_persona_documento"],
                "version_registro": row["version_registro"],
                "id_persona": row["id_persona"],
                "tipo_documento": row["tipo_documento_persona"],
                "numero_documento": row["numero_documento"],
                "pais_emision": row["pais_emision"],
                "es_principal": row["es_principal"],
            }
        except Exception:
            self.db.rollback()
            raise

    def update_relacion_persona_rol(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_relacion_persona_rol": values["id_relacion_persona_rol"],
            "id_persona": values["id_persona"],
            "id_rol_participacion": values["id_rol_participacion"],
            "tipo_relacion": values["tipo_relacion"],
            "id_relacion": values["id_relacion"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "observaciones": values["observaciones"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE relacion_persona_rol
            SET
                id_persona = :id_persona,
                id_rol_participacion = :id_rol_participacion,
                tipo_relacion = :tipo_relacion,
                id_relacion = :id_relacion,
                fecha_desde = :fecha_desde,
                fecha_hasta = :fecha_hasta,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_relacion_persona_rol = :id_relacion_persona_rol
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_relacion_persona_rol,
                id_persona,
                id_rol_participacion,
                tipo_relacion,
                id_relacion,
                version_registro,
                fecha_desde,
                fecha_hasta
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_relacion_persona_rol": row["id_relacion_persona_rol"],
                "id_persona": row["id_persona"],
                "id_rol_participacion": row["id_rol_participacion"],
                "tipo_relacion": row["tipo_relacion"],
                "id_relacion": row["id_relacion"],
                "version_registro": row["version_registro"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_relacion_persona_rol(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_relacion_persona_rol": values["id_relacion_persona_rol"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "deleted_at": values["deleted_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE relacion_persona_rol
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_relacion_persona_rol = :id_relacion_persona_rol
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_relacion_persona_rol,
                version_registro
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_relacion_persona_rol": row["id_relacion_persona_rol"],
                "version_registro": row["version_registro"],
            }
        except Exception:
            self.db.rollback()
            raise

    def update_persona_domicilio(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_persona_domicilio": values["id_persona_domicilio"],
            "tipo_domicilio": values["tipo_domicilio"],
            "direccion": values["direccion"],
            "localidad": values["localidad"],
            "provincia": values["provincia"],
            "pais": values["pais"],
            "codigo_postal": values["codigo_postal"],
            "es_principal": values["es_principal"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "observaciones": values["observaciones"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE persona_domicilio
            SET
                tipo_domicilio = :tipo_domicilio,
                direccion = :direccion,
                localidad = :localidad,
                provincia = :provincia,
                pais = :pais,
                codigo_postal = :codigo_postal,
                es_principal = :es_principal,
                fecha_desde = :fecha_desde,
                fecha_hasta = :fecha_hasta,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_persona_domicilio = :id_persona_domicilio
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_persona_domicilio,
                version_registro,
                id_persona,
                tipo_domicilio,
                direccion,
                localidad,
                provincia,
                pais,
                codigo_postal,
                es_principal
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_persona_domicilio": row["id_persona_domicilio"],
                "version_registro": row["version_registro"],
                "id_persona": row["id_persona"],
                "tipo_domicilio": row["tipo_domicilio"],
                "direccion": row["direccion"],
                "localidad": row["localidad"],
                "provincia": row["provincia"],
                "pais": row["pais"],
                "codigo_postal": row["codigo_postal"],
                "es_principal": row["es_principal"],
            }
        except Exception:
            self.db.rollback()
            raise
