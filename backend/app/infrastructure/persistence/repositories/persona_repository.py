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

    def list_personas(
        self,
        *,
        q: str | None,
        tipo_persona: str | None,
        estado_persona: str | None,
        numero_documento: str | None,
        cuit_cuil: str | None,
        tipo_documento: str | None,
        contacto: str | None,
        rol_codigo: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        filters = ["p.deleted_at IS NULL"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if q is not None:
            filters.append(
                """
                (
                    p.nombre ILIKE :q_like
                    OR p.apellido ILIKE :q_like
                    OR p.razon_social ILIKE :q_like
                    OR p.cuit_cuil ILIKE :q_like
                    OR EXISTS (
                        SELECT 1
                        FROM persona_documento pdq
                        WHERE pdq.id_persona = p.id_persona
                          AND pdq.deleted_at IS NULL
                          AND pdq.numero_documento ILIKE :q_like
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM persona_contacto pcq
                        WHERE pcq.id_persona = p.id_persona
                          AND pcq.deleted_at IS NULL
                          AND pcq.valor_contacto ILIKE :q_like
                    )
                )
                """
            )
            params["q_like"] = f"%{q}%"
        if tipo_persona is not None:
            filters.append("UPPER(p.tipo_persona) = :tipo_persona")
            params["tipo_persona"] = tipo_persona.upper()
        if estado_persona is not None:
            filters.append("UPPER(p.estado_persona) = :estado_persona")
            params["estado_persona"] = estado_persona.upper()
        if numero_documento is not None:
            filters.append(
                """
                EXISTS (
                    SELECT 1
                    FROM persona_documento pdf
                    WHERE pdf.id_persona = p.id_persona
                      AND pdf.deleted_at IS NULL
                      AND pdf.numero_documento ILIKE :numero_documento_like
                )
                """
            )
            params["numero_documento_like"] = f"%{numero_documento}%"
        if cuit_cuil is not None:
            filters.append("p.cuit_cuil ILIKE :cuit_cuil_like")
            params["cuit_cuil_like"] = f"%{cuit_cuil}%"
        if tipo_documento is not None:
            filters.append(
                """
                EXISTS (
                    SELECT 1
                    FROM persona_documento pdt
                    WHERE pdt.id_persona = p.id_persona
                      AND pdt.deleted_at IS NULL
                      AND UPPER(pdt.tipo_documento_persona) = :tipo_documento
                )
                """
            )
            params["tipo_documento"] = tipo_documento.upper()
        if contacto is not None:
            filters.append(
                """
                EXISTS (
                    SELECT 1
                    FROM persona_contacto pcf
                    WHERE pcf.id_persona = p.id_persona
                      AND pcf.deleted_at IS NULL
                      AND pcf.valor_contacto ILIKE :contacto_like
                )
                """
            )
            params["contacto_like"] = f"%{contacto}%"
        if rol_codigo is not None:
            filters.append(
                """
                EXISTS (
                    SELECT 1
                    FROM relacion_persona_rol rpr
                    JOIN rol_participacion rp
                      ON rp.id_rol_participacion = rpr.id_rol_participacion
                     AND rp.deleted_at IS NULL
                    WHERE rpr.id_persona = p.id_persona
                      AND rpr.deleted_at IS NULL
                      AND UPPER(rp.codigo_rol) = :rol_codigo
                )
                """
            )
            params["rol_codigo"] = rol_codigo.upper()

        where_clause = " AND ".join(filters)
        base_from = f"""
            FROM persona p
            WHERE {where_clause}
        """
        count_statement = text(f"SELECT COUNT(*) {base_from}")
        total = self.db.execute(count_statement, params).scalar_one()

        data_statement = text(
            f"""
            WITH personas_filtradas AS (
                SELECT
                    p.id_persona,
                    p.tipo_persona,
                    p.nombre,
                    p.apellido,
                    p.razon_social,
                    COALESCE(
                        NULLIF(BTRIM(p.razon_social), ''),
                        NULLIF(BTRIM(CONCAT_WS(' ', p.nombre, p.apellido)), ''),
                        CONCAT('Persona ', p.id_persona)
                    ) AS display_name,
                    p.estado_persona,
                    p.cuit_cuil
                {base_from}
                ORDER BY
                    CASE WHEN UPPER(p.estado_persona) = 'ACTIVA' THEN 0 ELSE 1 END,
                    COALESCE(
                        NULLIF(BTRIM(p.razon_social), ''),
                        NULLIF(BTRIM(CONCAT_WS(' ', p.nombre, p.apellido)), ''),
                        CONCAT('Persona ', p.id_persona)
                    ) ASC,
                    p.id_persona ASC
                LIMIT :limit OFFSET :offset
            )
            SELECT
                pf.id_persona,
                pf.tipo_persona,
                pf.nombre,
                pf.apellido,
                pf.razon_social,
                pf.display_name,
                pf.estado_persona,
                pf.cuit_cuil,
                dp.id_persona_documento,
                dp.tipo_documento_persona,
                dp.numero_documento,
                dp.pais_emision,
                cp.id_persona_contacto,
                cp.tipo_contacto,
                cp.valor_contacto
            FROM personas_filtradas pf
            LEFT JOIN LATERAL (
                SELECT
                    id_persona_documento,
                    tipo_documento_persona,
                    numero_documento,
                    pais_emision
                FROM persona_documento
                WHERE id_persona = pf.id_persona
                  AND deleted_at IS NULL
                  AND es_principal IS TRUE
                ORDER BY id_persona_documento ASC
                LIMIT 1
            ) dp ON TRUE
            LEFT JOIN LATERAL (
                SELECT
                    id_persona_contacto,
                    tipo_contacto,
                    valor_contacto
                FROM persona_contacto
                WHERE id_persona = pf.id_persona
                  AND deleted_at IS NULL
                  AND es_principal IS TRUE
                ORDER BY id_persona_contacto ASC
                LIMIT 1
            ) cp ON TRUE
            ORDER BY
                CASE WHEN UPPER(pf.estado_persona) = 'ACTIVA' THEN 0 ELSE 1 END,
                pf.display_name ASC,
                pf.id_persona ASC
            """
        )
        rows = self.db.execute(data_statement, params).mappings().all()
        items = []
        for row in rows:
            documento_principal = None
            if row["id_persona_documento"] is not None:
                documento_principal = {
                    "id_persona_documento": row["id_persona_documento"],
                    "tipo_documento_persona": row["tipo_documento_persona"],
                    "numero_documento": row["numero_documento"],
                    "pais_emision": row["pais_emision"],
                }
            contacto_principal = None
            if row["id_persona_contacto"] is not None:
                contacto_principal = {
                    "id_persona_contacto": row["id_persona_contacto"],
                    "tipo_contacto": row["tipo_contacto"],
                    "valor_contacto": row["valor_contacto"],
                }
            items.append(
                {
                    "id_persona": row["id_persona"],
                    "tipo_persona": row["tipo_persona"],
                    "nombre": row["nombre"],
                    "apellido": row["apellido"],
                    "razon_social": row["razon_social"],
                    "display_name": row["display_name"],
                    "estado_persona": row["estado_persona"],
                    "cuit_cuil": row["cuit_cuil"],
                    "documento_principal": documento_principal,
                    "contacto_principal": contacto_principal,
                }
            )

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
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

    def list_roles_participacion(
        self, codigo: str | None = None
    ) -> list[dict[str, Any]]:
        filters = ["deleted_at IS NULL", "UPPER(estado_rol) = 'ACTIVO'"]
        params: dict[str, Any] = {}
        if codigo is not None and codigo.strip():
            filters.append("UPPER(codigo_rol) = :codigo")
            params["codigo"] = codigo.strip().upper()

        statement = text(
            f"""
            SELECT id_rol_participacion, codigo_rol, nombre_rol, deleted_at
            FROM rol_participacion
            WHERE {' AND '.join(filters)}
            ORDER BY codigo_rol, id_rol_participacion
            """
        )
        rows = self.db.execute(statement, params).mappings().all()
        return [
            {
                "id_rol_participacion": row["id_rol_participacion"],
                "codigo_rol": row["codigo_rol"],
                "nombre_rol": row["nombre_rol"],
                "deleted_at": row["deleted_at"],
            }
            for row in rows
        ]

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
                version_registro,
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
                "version_registro": row["version_registro"],
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
                version_registro,
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
                "version_registro": row["version_registro"],
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
                es_principal,
                version_registro
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
                "version_registro": row["version_registro"],
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

    def get_persona_detalle_integral(self, id_persona: int) -> dict[str, Any] | None:
        persona = self.get_persona(id_persona)
        if persona is None:
            return None

        participaciones = self._get_persona_participaciones_detalle(id_persona)
        obligaciones = self._get_persona_obligaciones_financieras(id_persona)
        resumen = self._build_resumen_financiero(obligaciones)
        usos = self._get_persona_usos_transversales(id_persona, resumen)

        return {
            **persona,
            "documentos": self.get_persona_documentos(id_persona),
            "domicilios": self.get_persona_domicilios(id_persona),
            "contactos": self.get_persona_contactos(id_persona),
            "relaciones": self.get_persona_relaciones(id_persona),
            "representaciones_poder": self.get_representaciones_poder(id_persona),
            "participaciones": participaciones,
            "obligaciones_financieras": obligaciones,
            "resumen_financiero": resumen,
            "usos_transversales": usos,
        }

    def _get_persona_participaciones_detalle(
        self, id_persona: int
    ) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                rpr.id_relacion_persona_rol,
                rpr.id_persona,
                rpr.id_rol_participacion,
                rp.codigo_rol,
                rp.nombre_rol,
                rp.estado_rol,
                rpr.tipo_relacion,
                rpr.id_relacion,
                rpr.fecha_desde,
                rpr.fecha_hasta
            FROM relacion_persona_rol rpr
            LEFT JOIN rol_participacion rp
              ON rp.id_rol_participacion = rpr.id_rol_participacion
             AND rp.deleted_at IS NULL
            WHERE rpr.id_persona = :id_persona
              AND rpr.deleted_at IS NULL
            ORDER BY rpr.id_relacion_persona_rol
            """
        )
        rows = self.db.execute(statement, {"id_persona": id_persona}).mappings().all()
        return [
            {
                "id_relacion_persona_rol": row["id_relacion_persona_rol"],
                "id_persona": row["id_persona"],
                "id_rol_participacion": row["id_rol_participacion"],
                "codigo_rol": row["codigo_rol"],
                "nombre_rol": row["nombre_rol"],
                "estado_rol": row["estado_rol"],
                "tipo_relacion": row["tipo_relacion"],
                "id_relacion": row["id_relacion"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
            }
            for row in rows
        ]

    def _get_persona_obligaciones_financieras(
        self, id_persona: int
    ) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                oo.id_obligacion_obligado,
                o.id_obligacion_financiera,
                o.id_relacion_generadora,
                rg.tipo_origen,
                rg.id_origen,
                oo.rol_obligado,
                oo.porcentaje_responsabilidad,
                o.fecha_emision,
                o.fecha_vencimiento,
                o.estado_obligacion,
                o.importe_total,
                o.saldo_pendiente,
                o.moneda
            FROM obligacion_obligado oo
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = oo.id_obligacion_financiera
             AND o.deleted_at IS NULL
            JOIN relacion_generadora rg
              ON rg.id_relacion_generadora = o.id_relacion_generadora
             AND rg.deleted_at IS NULL
            WHERE oo.id_persona = :id_persona
              AND oo.deleted_at IS NULL
            ORDER BY o.fecha_vencimiento ASC NULLS LAST, o.id_obligacion_financiera ASC
            """
        )
        rows = self.db.execute(statement, {"id_persona": id_persona}).mappings().all()
        obligaciones: list[dict[str, Any]] = []
        for row in rows:
            porcentaje = row["porcentaje_responsabilidad"]
            pct = float(porcentaje) if porcentaje is not None else 0.0
            importe_total = float(row["importe_total"])
            saldo_pendiente = float(row["saldo_pendiente"])
            obligaciones.append(
                {
                    "id_obligacion_obligado": row["id_obligacion_obligado"],
                    "id_obligacion_financiera": row["id_obligacion_financiera"],
                    "id_relacion_generadora": row["id_relacion_generadora"],
                    "tipo_origen": str(row["tipo_origen"]).upper(),
                    "id_origen": row["id_origen"],
                    "rol_obligado": row["rol_obligado"],
                    "porcentaje_responsabilidad": pct if porcentaje is not None else None,
                    "fecha_emision": row["fecha_emision"],
                    "fecha_vencimiento": row["fecha_vencimiento"],
                    "estado_obligacion": row["estado_obligacion"],
                    "importe_total": importe_total,
                    "saldo_pendiente": saldo_pendiente,
                    "moneda": row["moneda"],
                    "monto_responsabilidad": round(importe_total * pct / 100, 2),
                    "saldo_responsabilidad": round(saldo_pendiente * pct / 100, 2),
                }
            )
        return obligaciones

    def _build_resumen_financiero(
        self, obligaciones: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return {
            "cantidad_obligaciones": len(obligaciones),
            "importe_total": round(sum(o["importe_total"] for o in obligaciones), 2),
            "saldo_pendiente_total": round(
                sum(o["saldo_pendiente"] for o in obligaciones), 2
            ),
            "importe_total_responsabilidad": round(
                sum(o["monto_responsabilidad"] for o in obligaciones), 2
            ),
            "saldo_pendiente_responsabilidad": round(
                sum(o["saldo_responsabilidad"] for o in obligaciones), 2
            ),
        }

    def _get_persona_usos_transversales(
        self, id_persona: int, resumen_financiero: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "comprador_ventas": self._get_persona_usos_ventas(id_persona),
            "contratos_locativos": self._get_persona_usos_contratos(id_persona),
            "servicios_responsable": self._get_persona_usos_servicios(id_persona),
            "obligado_financiero": resumen_financiero,
        }

    def _get_persona_usos_ventas(self, id_persona: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                v.id_venta,
                v.codigo_venta,
                v.estado_venta,
                v.monto_total,
                v.moneda,
                rp.codigo_rol
            FROM relacion_persona_rol rpr
            JOIN rol_participacion rp
              ON rp.id_rol_participacion = rpr.id_rol_participacion
             AND rp.deleted_at IS NULL
            JOIN venta v
              ON v.id_venta = rpr.id_relacion
             AND v.deleted_at IS NULL
            WHERE rpr.id_persona = :id_persona
              AND rpr.deleted_at IS NULL
              AND LOWER(rpr.tipo_relacion) = 'venta'
              AND UPPER(rp.codigo_rol) = 'COMPRADOR'
            ORDER BY v.id_venta
            """
        )
        rows = self.db.execute(statement, {"id_persona": id_persona}).mappings().all()
        return [
            {
                "id_venta": row["id_venta"],
                "codigo_venta": row["codigo_venta"],
                "estado_venta": row["estado_venta"],
                "monto_total": float(row["monto_total"]) if row["monto_total"] is not None else None,
                "moneda": row["moneda"],
                "rol": row["codigo_rol"],
            }
            for row in rows
        ]

    def _get_persona_usos_contratos(self, id_persona: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                ca.id_contrato_alquiler,
                ca.codigo_contrato,
                ca.estado_contrato,
                ca.fecha_inicio,
                ca.fecha_fin,
                rp.codigo_rol
            FROM relacion_persona_rol rpr
            JOIN rol_participacion rp
              ON rp.id_rol_participacion = rpr.id_rol_participacion
             AND rp.deleted_at IS NULL
            JOIN contrato_alquiler ca
              ON ca.id_contrato_alquiler = rpr.id_relacion
             AND ca.deleted_at IS NULL
            WHERE rpr.id_persona = :id_persona
              AND rpr.deleted_at IS NULL
              AND LOWER(rpr.tipo_relacion) IN ('contrato_alquiler', 'contrato')
              AND UPPER(rp.codigo_rol) IN (
                  'LOCATARIO', 'LOCATARIO_PRINCIPAL', 'GARANTE', 'LOCADOR'
              )
            ORDER BY ca.id_contrato_alquiler
            """
        )
        rows = self.db.execute(statement, {"id_persona": id_persona}).mappings().all()
        return [
            {
                "id_contrato_alquiler": row["id_contrato_alquiler"],
                "codigo_contrato": row["codigo_contrato"],
                "estado_contrato": row["estado_contrato"],
                "fecha_inicio": row["fecha_inicio"],
                "fecha_fin": row["fecha_fin"],
                "rol": row["codigo_rol"],
            }
            for row in rows
        ]

    def _get_persona_usos_servicios(self, id_persona: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_asignacion_servicio_responsable,
                id_servicio,
                id_inmueble,
                id_unidad_funcional,
                porcentaje_responsabilidad,
                fecha_desde,
                fecha_hasta,
                estado_asignacion
            FROM asignacion_servicio_responsable
            WHERE id_persona = :id_persona
              AND deleted_at IS NULL
            ORDER BY id_asignacion_servicio_responsable
            """
        )
        rows = self.db.execute(statement, {"id_persona": id_persona}).mappings().all()
        return [
            {
                "id_asignacion_servicio_responsable": row[
                    "id_asignacion_servicio_responsable"
                ],
                "id_servicio": row["id_servicio"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "porcentaje_responsabilidad": float(
                    row["porcentaje_responsabilidad"]
                ),
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
                "estado_asignacion": row["estado_asignacion"],
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

    def update_datos_principales_tx(self, command: Any) -> dict[str, Any] | None:
        from datetime import UTC, datetime
        from uuid import uuid4

        fiscal_types = {"CUIT", "CUIL", "CDI"}
        now = datetime.now(UTC)
        id_instalacion = command.context.id_instalacion
        op_id = command.context.op_id

        def doc_to_payload(doc: Any) -> dict[str, Any] | None:
            if doc is None:
                return None
            tipo = (doc.tipo_documento or "").strip().upper()
            numero = (doc.numero_documento or "").strip()
            if doc.id_persona_documento is not None and not numero:
                raise ValueError("numero_documento es requerido para actualizar un documento existente.")
            if doc.id_persona_documento is None and not numero:
                return None
            return {
                "id_persona_documento": doc.id_persona_documento,
                "tipo_documento": tipo,
                "numero_documento": numero,
                "pais_emision": doc.pais_emision,
                "es_principal": doc.es_principal,
                "version_registro": doc.version_registro,
            }

        identidad = doc_to_payload(command.documento_identidad)
        fiscal = doc_to_payload(command.identificacion_fiscal)
        try:
            persona = self.get_persona_for_update(command.id_persona)
            if persona is None:
                raise ValueError("NOT_FOUND_PERSONA")
            if persona["version_registro"] != command.persona.version_registro:
                self.db.rollback()
                return None

            row = self.db.execute(text("""
                UPDATE persona
                SET tipo_persona=:tipo_persona, nombre=:nombre, apellido=:apellido,
                    razon_social=:razon_social, fecha_nacimiento_constitucion=:fecha_nacimiento,
                    estado_persona=:estado_persona, observaciones=:observaciones,
                    version_registro=:version_nueva, updated_at=:updated_at,
                    id_instalacion_ultima_modificacion=:id_instalacion,
                    op_id_ultima_modificacion=:op_id
                WHERE id_persona=:id_persona AND version_registro=:version_actual AND deleted_at IS NULL
                RETURNING id_persona, version_registro, tipo_persona, nombre, apellido,
                          razon_social, fecha_nacimiento_constitucion, estado_persona, observaciones
            """), {
                "id_persona": command.id_persona,
                "tipo_persona": command.persona.tipo_persona,
                "nombre": command.persona.nombre,
                "apellido": command.persona.apellido,
                "razon_social": command.persona.razon_social,
                "fecha_nacimiento": command.persona.fecha_nacimiento,
                "estado_persona": command.persona.estado_persona,
                "observaciones": command.persona.observaciones,
                "version_actual": command.persona.version_registro,
                "version_nueva": command.persona.version_registro + 1,
                "updated_at": now,
                "id_instalacion": id_instalacion,
                "op_id": op_id,
            }).mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None

            def upsert_doc(doc: dict[str, Any] | None) -> None:
                if doc is None:
                    return True
                if doc["tipo_documento"] in fiscal_types:
                    dup_filter = "UPPER(tipo_documento_persona) IN ('CUIT','CUIL','CDI')"
                else:
                    dup_filter = "UPPER(tipo_documento_persona) NOT IN ('CUIT','CUIL','CDI') AND es_principal IS TRUE"
                duplicate = self.db.execute(text(f"""
                    SELECT id_persona_documento FROM persona_documento
                    WHERE id_persona=:id_persona AND deleted_at IS NULL AND {dup_filter}
                      AND (:id_doc IS NULL OR id_persona_documento <> :id_doc)
                    LIMIT 1
                """), {"id_persona": command.id_persona, "id_doc": doc["id_persona_documento"]}).scalar_one_or_none()
                if duplicate is not None:
                    raise ValueError("DUPLICATE_ACTIVE_DOCUMENT")
                if doc["id_persona_documento"] is None:
                    self.db.execute(text("""
                        INSERT INTO persona_documento (
                            uid_global, version_registro, created_at, updated_at,
                            id_instalacion_origen, id_instalacion_ultima_modificacion,
                            op_id_alta, op_id_ultima_modificacion, id_persona,
                            tipo_documento_persona, numero_documento, pais_emision,
                            es_principal, fecha_desde, fecha_hasta, observaciones
                        ) VALUES (
                            :uid_global, 1, :now, :now, :id_instalacion, :id_instalacion,
                            :op_id, :op_id, :id_persona, :tipo, :numero, :pais,
                            :principal, :now, NULL, NULL
                        )
                    """), {"uid_global": str(uuid4()), "now": now, "id_instalacion": id_instalacion, "op_id": op_id,
                            "id_persona": command.id_persona, "tipo": doc["tipo_documento"], "numero": doc["numero_documento"],
                            "pais": doc["pais_emision"], "principal": doc["es_principal"]})
                    return True
                current = self.db.execute(text("""
                    SELECT id_persona, version_registro FROM persona_documento
                    WHERE id_persona_documento=:id_doc AND deleted_at IS NULL
                """), {"id_doc": doc["id_persona_documento"]}).mappings().one_or_none()
                if current is None or current["id_persona"] != command.id_persona:
                    raise ValueError("NOT_FOUND_DOCUMENTO")
                if doc["version_registro"] is None or current["version_registro"] != doc["version_registro"]:
                    return None
                updated = self.db.execute(text("""
                    UPDATE persona_documento
                    SET tipo_documento_persona=:tipo, numero_documento=:numero, pais_emision=:pais,
                        es_principal=:principal, version_registro=:version_nueva, updated_at=:now,
                        id_instalacion_ultima_modificacion=:id_instalacion, op_id_ultima_modificacion=:op_id
                    WHERE id_persona_documento=:id_doc AND version_registro=:version_actual AND deleted_at IS NULL
                    RETURNING id_persona_documento
                """), {"id_doc": doc["id_persona_documento"], "tipo": doc["tipo_documento"], "numero": doc["numero_documento"],
                        "pais": doc["pais_emision"], "principal": doc["es_principal"], "version_actual": doc["version_registro"],
                        "version_nueva": doc["version_registro"] + 1, "now": now, "id_instalacion": id_instalacion, "op_id": op_id}).scalar_one_or_none()
                if updated is None:
                    return None
                return True

            for doc in (identidad, fiscal):
                result = upsert_doc(doc)
                if result is None:
                    self.db.rollback()
                    return None
            self.db.commit()
            persona_actualizada = self.get_persona(command.id_persona)
            if persona_actualizada is None:
                raise ValueError("NOT_FOUND_PERSONA")
            return {
                **persona_actualizada,
                "documentos": self.get_persona_documentos(command.id_persona),
                "domicilios": self.get_persona_domicilios(command.id_persona),
                "contactos": self.get_persona_contactos(command.id_persona),
                "relaciones": self.get_persona_relaciones(command.id_persona),
                "representaciones_poder": self.get_representaciones_poder(command.id_persona),
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
