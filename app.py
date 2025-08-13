# Importaciones estándar de Python
import json
import os
from datetime import datetime

# Librerías externas
import google.generativeai as genai
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()

# Módulos locales
from database import get_db_connection, initialize_database

app = Flask(__name__)
CORS(app)  # Permitir peticiones desde frontend


# Asegurarse de que la estructura de base de datos exista
initialize_database()

# ------------------------
# Consejo del día
# ------------------------
print("DEBUG GEMINI_API_KEY:", os.getenv("GOOGLE_API_KEY"))
if not os.getenv("GEMINI_API_KEY"):
    raise ValueError("No se encontró GOOGLE_API_KEY en las variables de entorno.")
genai.configure(api_key = os.getenv("GOOGLE_API_KEY")) #La api key para usar openai
# Elegir el modelo de Gemini
model = genai.GenerativeModel("gemini-1.5-flash")

CONSEJO_FILE = "consejo.json"

def obtener_consejo():
    hoy = datetime.now().strftime("%Y-%m-%d")

    # Verificar si el archivo existe y contiene datos válidos
    if os.path.exists(CONSEJO_FILE):
        try:
            with open(CONSEJO_FILE, "r", encoding="utf-8") as f:
                contenido = f.read().strip()
                if contenido:  # solo intentar parsear si no está vacío
                    data = json.loads(contenido)
                    if data.get("fecha") == hoy:
                        return data["consejo"]
        except (json.JSONDecodeError, KeyError):
            # Si el archivo está corrupto o incompleto, seguimos y lo sobreescribimos
            pass

    # Si no existe, está vacío o es otro día → pedir nuevo consejo
    prompt = "Dame un consejo financiero breve y práctico para campesinos en Colombia."
    response = model.generate_content(prompt)
    consejo = response.text.strip()

    # Guardar el nuevo consejo
    with open(CONSEJO_FILE, "w", encoding="utf-8") as f:
        json.dump({"fecha": hoy, "consejo": consejo}, f, ensure_ascii=False, indent=2)

    return consejo


# ------------------------
# Simulador de crédito
# ------------------------

@app.route('/api/credito', methods=['POST'])
def crear_simulacion_credito():
    data = request.get_json()
    required = [
        'nombres', 'apellidos', 'documento_identidad', 'edad',
        'fecha_nacimiento', 'ingresos_mensuales', 'gastos_mensuales',
        'valor_patrimonio', 'dimension_terreno', 'destinacion_credito',
        'numero_empleados'
    ]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Falta campo {field}"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO simulaciones_credito (
                nombres, apellidos, documento_identidad, edad,
                fecha_nacimiento, ingresos_mensuales, gastos_mensuales,
                valor_patrimonio, dimension_terreno, destinacion_credito,
                numero_empleados
            ) VALUES (
                %(nombres)s, %(apellidos)s, %(documento_identidad)s, %(edad)s,
                %(fecha_nacimiento)s, %(ingresos_mensuales)s, %(gastos_mensuales)s,
                %(valor_patrimonio)s, %(dimension_terreno)s, %(destinacion_credito)s,
                %(numero_empleados)s
            )
            RETURNING *;
        """, {
            'nombres': data['nombres'],
            'apellidos': data['apellidos'],
            'documento_identidad': data['documento_identidad'],
            'edad': data['edad'],
            'fecha_nacimiento': data['fecha_nacimiento'],
            'ingresos_mensuales': data['ingresos_mensuales'],
            'gastos_mensuales': data['gastos_mensuales'],
            'valor_patrimonio': data['valor_patrimonio'],
            'dimension_terreno': data['dimension_terreno'],
            'destinacion_credito': data['destinacion_credito'],
            'numero_empleados': data['numero_empleados']
        })
        nueva = cur.fetchone()
        conn.commit()
        return jsonify(nueva), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Ocurrió un error: {e}"}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/credito', methods=['GET'])
def obtener_simulaciones_por_cedula():
    cedula = request.args.get('cedula')
    if not cedula:
        return jsonify({"error": "Se requiere parámetro 'cedula'"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM simulaciones_credito
            WHERE documento_identidad = %s
            ORDER BY created_at DESC;
        """, (cedula,))
        rows = cur.fetchall()
        return jsonify(rows), 200
    except Exception as e:
        return jsonify({"error": f"Error al consultar: {e}"}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/credito/<int:sim_id>', methods=['PUT'])
def actualizar_simulacion_credito(sim_id):
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No conexión"}), 500
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Actualiza solo los campos presentes
        updates = []
        params = {}
        allowed = [
            'nombres', 'apellidos', 'documento_identidad', 'edad',
            'fecha_nacimiento', 'ingresos_mensuales', 'gastos_mensuales',
            'valor_patrimonio', 'dimension_terreno', 'destinacion_credito',
            'numero_empleados'
        ]
        for field in allowed:
            if field in data:
                updates.append(f"{field} = %({field})s")
                params[field] = data[field]
        if not updates:
            return jsonify({"error": "No hay campos para actualizar"}), 400
        params['id'] = sim_id
        query = f"""
            UPDATE simulaciones_credito
            SET {', '.join(updates)}
            WHERE id = %(id)s
            RETURNING *;
        """
        cur.execute(query, params)
        updated = cur.fetchone()
        if not updated:
            return jsonify({"error": "Simulación no encontrada"}), 404
        conn.commit()
        return jsonify(updated), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Error actualizando: {e}"}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/credito/<int:sim_id>', methods=['DELETE'])
def eliminar_simulacion_credito(sim_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No conexión"}), 500
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM simulaciones_credito WHERE id = %s;", (sim_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "No se encontró la simulación"}), 404
        conn.commit()
        return jsonify({"mensaje": "Eliminado"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Error eliminando: {e}"}), 500
    finally:
        cur.close()
        conn.close()


# ------------------------
# Planilla financiera
# ------------------------

@app.route('/api/planilla', methods=['POST'])
def crear_planilla():
    data = request.get_json()
    required = ['cedula', 'ingresos', 'gastos', 'inversiones']
    for field in required:
        if field not in data:
            return jsonify({"error": f"Falta campo {field}"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No conexión"}), 500
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO planillas_financieras (
                cedula, ingresos, gastos, inversiones, observaciones
            ) VALUES (
                %(cedula)s, %(ingresos)s, %(gastos)s, %(inversiones)s, %(observaciones)s
            ) RETURNING *;
        """, {
            'cedula': data['cedula'],
            'ingresos': data['ingresos'],
            'gastos': data['gastos'],
            'inversiones': data['inversiones'],
            'observaciones': data.get('observaciones', '')
        })
        nueva = cur.fetchone()
        conn.commit()
        # Calcular utilidad manualmente
        utilidad = (nueva['ingresos'] or 0) - (nueva['gastos'] or 0) - (nueva['inversiones'] or 0)
        nueva['utilidad'] = float(utilidad)
        return jsonify(nueva), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Error creando planilla: {e}"}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/planilla', methods=['GET'])
def obtener_planillas_por_cedula():
    cedula = request.args.get('cedula')
    if not cedula:
        return jsonify({"error": "Se requiere 'cedula'"}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No conexión"}), 500
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT *,
                (ingresos - gastos - inversiones) AS utilidad
            FROM planillas_financieras
            WHERE cedula = %s
            ORDER BY fecha DESC;
        """, (cedula,))
        rows = cur.fetchall()
        return jsonify(rows), 200
    except Exception as e:
        return jsonify({"error": f"Error consultando: {e}"}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/planilla/<int:plan_id>', methods=['PUT'])
def actualizar_planilla(plan_id):
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No conexión"}), 500
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        updates = []
        params = {}
        allowed = ['cedula', 'ingresos', 'gastos', 'inversiones', 'observaciones']
        for field in allowed:
            if field in data:
                updates.append(f"{field} = %({field})s")
                params[field] = data[field]
        if not updates:
            return jsonify({"error": "Nada que actualizar"}), 400
        params['id'] = plan_id
        query = f"""
            UPDATE planillas_financieras
            SET {', '.join(updates)}
            WHERE id = %(id)s
            RETURNING *, (ingresos - gastos - inversiones) AS utilidad;
        """
        cur.execute(query, params)
        updated = cur.fetchone()
        if not updated:
            return jsonify({"error": "No encontrada"}), 404
        conn.commit()
        return jsonify(updated), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Error actualizando: {e}"}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/planilla/<int:plan_id>', methods=['DELETE'])
def eliminar_planilla(plan_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No conexión"}), 500
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM planillas_financieras WHERE id = %s;", (plan_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "No existe"}), 404
        conn.commit()
        return jsonify({"mensaje": "Eliminada"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Error eliminando: {e}"}), 500
    finally:
        cur.close()
        conn.close()


# ------------------------
# Contacto
# ------------------------

@app.route('/api/contacto', methods=['POST'])
def crear_contacto():
    data = request.get_json()
    required = ['nombres', 'correo', 'mensaje']
    for field in required:
        if field not in data:
            return jsonify({"error": f"Falta campo {field}"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No conexión"}), 500
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO contactos (
                nombres, apellidos, cedula, correo, celular, ubicacion, direccion, mensaje
            ) VALUES (
                %(nombres)s, %(apellidos)s, %(cedula)s, %(correo)s, %(celular)s, %(ubicacion)s, %(direccion)s, %(mensaje)s
            ) RETURNING *;
        """, {
            'nombres': data['nombres'],
            'apellidos': data.get('apellidos', ''),
            'cedula': data.get('cedula', ''),
            'correo': data['correo'],
            'celular': data.get('celular', ''),
            'ubicacion': data.get('ubicacion', ''),
            'direccion': data.get('direccion', ''),
            'mensaje': data['mensaje']
        })
        nuevo = cur.fetchone()
        conn.commit()
        return jsonify(nuevo), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Error creando contacto: {e}"}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/contacto', methods=['GET'])
def listar_contactos():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No conexión"}), 500
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM contactos ORDER BY created_at DESC;")
        rows = cur.fetchall()
        return jsonify(rows), 200
    except Exception as e:
        return jsonify({"error": f"Error listando contactos: {e}"}), 500
    finally:
        cur.close()
        conn.close()


# ------------------------
# Health check / raíz
# ------------------------

@app.route('/')
def index():
    consejo = obtener_consejo()
    return render_template('index.html', consejo=consejo)

@app.route('/credito')
def credito():
    return render_template('credito.html')
 
@app.route('/planilla')
def planilla():
    return render_template('planilla.html')
    
@app.route('/noticias')
def noticias():
    return render_template('noticias.html')
    
@app.route('/contacto')
def contacto():
    return render_template('contacto.html')

if __name__ == '__main__':
    app.run(debug=True)
