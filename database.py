# database.py
import os
import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("No se encontró la variable de entorno DATABASE_URL")


def get_db_connection():
    """Establece conexión con PostgreSQL."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"[DB] Error al conectar a la base de datos: {e}")
        return None


def initialize_database():
    """Crea la función, tablas y trigger necesarios si no existen."""
    conn = get_db_connection()
    if not conn:
        return
    cur = conn.cursor()
    try:
        # 1. Función para cálculo de crédito aprobado
        cur.execute("""
        CREATE OR REPLACE FUNCTION calcular_credito_aprobado(
            ingresos NUMERIC,
            gastos NUMERIC,
            patrimonio NUMERIC
        ) RETURNS NUMERIC AS $$
        DECLARE
            capacidad NUMERIC;
            aprobado NUMERIC;
        BEGIN
            capacidad := GREATEST(ingresos - gastos, 0);
            aprobado := capacidad * 6 + patrimonio * 0.10;
            RETURN ROUND(aprobado, 2);
        END;
        $$ LANGUAGE plpgsql;
        """)

        # 2. Tabla simulador de crédito
        cur.execute("""
        CREATE TABLE IF NOT EXISTS simulaciones_credito (
            id SERIAL PRIMARY KEY,
            fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            nombres TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            documento_identidad TEXT NOT NULL,
            edad INTEGER,
            fecha_nacimiento DATE,
            ingresos_mensuales NUMERIC DEFAULT 0,
            gastos_mensuales NUMERIC DEFAULT 0,
            valor_patrimonio NUMERIC DEFAULT 0,
            dimension_terreno TEXT,
            destinacion_credito TEXT,
            numero_empleados INTEGER DEFAULT 0,
            valor_aprobado NUMERIC,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
        """)

        # 3. Trigger function para actualizar valor_aprobado
        cur.execute("""
        CREATE OR REPLACE FUNCTION actualizar_credito_aprobado_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.valor_aprobado := calcular_credito_aprobado(
                COALESCE(NEW.ingresos_mensuales, 0),
                COALESCE(NEW.gastos_mensuales, 0),
                COALESCE(NEW.valor_patrimonio, 0)
            );
            NEW.updated_at := NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # 4. Crear trigger asociado (elimina el viejo si lo hay)
        cur.execute("""
        DROP TRIGGER IF EXISTS trg_credito_aprobado ON simulaciones_credito;
        CREATE TRIGGER trg_credito_aprobado
        BEFORE INSERT OR UPDATE ON simulaciones_credito
        FOR EACH ROW
        EXECUTE FUNCTION actualizar_credito_aprobado_trigger();
        """)

        # 5. Tabla planilla financiera (sin columna generada de utilidad)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS planillas_financieras (
            id SERIAL PRIMARY KEY,
            cedula TEXT NOT NULL,
            fecha DATE DEFAULT CURRENT_DATE,
            ingresos NUMERIC DEFAULT 0,
            gastos NUMERIC DEFAULT 0,
            inversiones NUMERIC DEFAULT 0,
            observaciones TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
        """)

        # 6. Tabla de contactos
        cur.execute("""
        CREATE TABLE IF NOT EXISTS contactos (
            id SERIAL PRIMARY KEY,
            nombres TEXT NOT NULL,
            apellidos TEXT,
            cedula TEXT,
            correo TEXT,
            celular TEXT,
            ubicacion TEXT,
            direccion TEXT,
            mensaje TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
        """)

        conn.commit()
        print("[DB] Inicialización de la base de datos completada.")
    except Exception as e:
        print(f"[DB] Error al inicializar la base de datos: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    initialize_database()
