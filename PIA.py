import sqlite3
import os
import datetime
import json
from tabulate import tabulate

DB_NAME = "coworking.db"
TURNOS = ("Matutino", "Vespertino", "Nocturno")

def inicializar_db():
    existe = os.path.exists(DB_NAME)
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Clientes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombres TEXT NOT NULL CHECK(trim(nombres) <> ''),
                apellidos TEXT NOT NULL CHECK(trim(apellidos) <> '')
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Salas(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL CHECK(trim(nombre) <> ''),
                cupo INTEGER NOT NULL CHECK(cupo > 0)
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Reservaciones(
                folio INTEGER PRIMARY KEY AUTOINCREMENT,
                id_cliente INTEGER NOT NULL,
                id_sala INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                turno TEXT NOT NULL,
                evento TEXT NOT NULL CHECK(trim(evento) <> ''),
                FOREIGN KEY(id_cliente) REFERENCES Clientes(id),
                FOREIGN KEY(id_sala) REFERENCES Salas(id),
                UNIQUE(id_sala, fecha, turno)
            )
            """)
            conn.commit()
        if not existe:
            print("No se encontró estado previo, iniciando con estado inicial vacío.")
        else:
            print("Se cargó una versión previa del estado de la solución.")
    except Exception as e:
        print("Error al inicializar la base de datos:", e)

def listar_clientes_tabla():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, apellidos, nombres FROM Clientes ORDER BY apellidos, nombres")
            rows = cursor.fetchall()
            if not rows:
                print("No hay clientes registrados.")
                return []
            headers = ["CLAVE", "APELLIDOS, NOMBRES"]
            table = [(r[0], f"{r[1]}, {r[2]}") for r in rows]
            print(tabulate(table, headers=headers, tablefmt="grid"))
            return [r[0] for r in rows]
    except Exception as e:
        print("Error al listar clientes:", e)
        return []

def registrar_cliente():
    print("\nRegistrar nuevo cliente")
    try:
        while True:
            nombres = input("Nombres: ").strip()
            if nombres:
                break
            print("El nombre no puede omitirse.")
        while True:
            apellidos = input("Apellidos: ").strip()
            if apellidos:
                break
            print("Los apellidos no pueden omitirse.")
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Clientes (nombres, apellidos) VALUES (?, ?)", (nombres, apellidos))
            conn.commit()
            print(f"Cliente registrado con clave {cursor.lastrowid}.")
    except Exception as e:
        print("Error al registrar cliente:", e)

def registrar_sala():
    print("\nRegistrar nueva sala")
    try:
        while True:
            nombre = input("Nombre de la sala: ").strip()
            if nombre:
                break
            print("El nombre de la sala no puede omitirse.")
        while True:
            try:
                cupo = int(input("Cupo (entero > 0): "))
                if cupo > 0:
                    break
                print("El cupo debe ser mayor a cero.")
            except ValueError:
                print("Debe ingresar un número entero.")
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Salas (nombre, cupo) VALUES (?, ?)", (nombre, cupo))
            conn.commit()
            print(f"Sala registrada con clave {cursor.lastrowid}.")
    except Exception as e:
        print("Error al registrar sala:", e)

def obtener_salas():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, cupo FROM Salas ORDER BY nombre")
            return cursor.fetchall()
    except Exception as e:
        print("Error al obtener salas:", e)
        return []

def salas_con_turnos_libres(fecha_str):
    libres = []
    try:
        salas = obtener_salas()
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            for id_sala, nombre, cupo in salas:
                cursor.execute("SELECT turno FROM Reservaciones WHERE id_sala = ? AND fecha = ?", (id_sala, fecha_str))
                ocupados = {row[0] for row in cursor.fetchall()}
                turnos_libres = [t for t in TURNOS if t not in ocupados]
                if turnos_libres:
                    libres.append((id_sala, nombre, cupo, turnos_libres))
        return libres
    except Exception as e:
        print("Error al consultar turnos libres:", e)
        return []

def validar_fecha_str(fecha_txt):
    try:
        return datetime.datetime.strptime(fecha_txt, "%m-%d-%Y").date()
    except:
        return None

def proponer_lunes_si_es_domingo(fecha):
    if fecha.weekday() == 6:
        return fecha + datetime.timedelta(days=1)
    return fecha

def registrar_reservacion():
    print("\nRegistrar reservación de sala")
    try:
        clientes_ids = listar_clientes_tabla()
        if not clientes_ids:
            return
        while True:
            clave = input("Elige la clave del cliente (o 0 para cancelar): ").strip()
            if clave == "0":
                print("Operación cancelada.")
                return
            try:
                id_cliente = int(clave)
            except ValueError:
                print("La clave debe ser numérica.")
                continue
            if id_cliente not in clientes_ids:
                print("Clave no encontrada. Te muestro la lista otra vez.")
                clientes_ids = listar_clientes_tabla()
                if not clientes_ids:
                    return
                opcion = input("¿Deseas cancelar la operación? (S/N): ").strip().upper()
                if opcion == "S":
                    print("Operación cancelada.")
                    return
                continue
            break

        hoy = datetime.date.today()
        fecha_minima = hoy + datetime.timedelta(days=2)
        while True:
            fecha_txt = input(f"Fecha (MM-DD-AAAA). Debe ser >= {fecha_minima.strftime('%m-%d-%Y')}: ").strip()
            fecha = validar_fecha_str(fecha_txt)
            if not fecha:
                print("Formato inválido. Usa MM-DD-AAAA.")
                continue
            if fecha < fecha_minima:
                print("La reserva debe hacerse con al menos dos días de anticipación.")
                continue
            if fecha.weekday() == 6:
                lunes = fecha + datetime.timedelta(days=1)
                print("No se permiten reservaciones en domingo.")
                usar = input(f"¿Desea usar el lunes siguiente ({lunes.strftime('%m-%d-%Y')})? (S/N): ").strip().upper()
                if usar == "S":
                    fecha = lunes
                    fecha_txt = fecha.strftime("%m-%d-%Y")
                else:
                    continue
            fecha_txt = fecha.strftime("%m-%d-%Y")
            break

        libres = salas_con_turnos_libres(fecha_txt)
        if not libres:
            print("No hay salas con turnos disponibles para la fecha seleccionada.")
            return

        print("\nSalas con turnos libres para esa fecha (se muestran nombre y cupo y turnos libres):")
        table = []
        for id_sala, nombre, cupo, turnos_libres in libres:
            table.append((id_sala, nombre, cupo, ", ".join(turnos_libres)))
        print(tabulate(table, headers=["ID", "SALA", "CUPO", "TURNOS LIBRES"], tablefmt="grid"))

        while True:
            try:
                id_sala_sel = int(input("Elige el ID de la sala: "))
            except ValueError:
                print("ID inválido.")
                continue
            posibles = {s[0]: s for s in libres}
            if id_sala_sel not in posibles:
                print("Esa sala no aparece como disponible para esa fecha.")
                continue
            break

        turnos_disponibles = posibles[id_sala_sel][3]
        print("Turnos disponibles para la sala elegida:", ", ".join(turnos_disponibles))
        while True:
            turno = input("Elige el turno (Matutino, Vespertino, Nocturno): ").strip().capitalize()
            if turno not in TURNOS:
                print("Turno inválido.")
                continue
            if turno not in turnos_disponibles:
                print("Ese turno no está disponible para la sala seleccionada en la fecha indicada.")
                continue
            break

        while True:
            evento = input("Nombre del evento: ").strip()
            if evento and evento.strip():
                break
            print("El nombre del evento no puede dejarse vacío ni ser solo espacios.")

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO Reservaciones (id_cliente, id_sala, fecha, turno, evento)
                    VALUES (?, ?, ?, ?, ?)
                """, (id_cliente, id_sala_sel, fecha_txt, turno, evento))
                conn.commit()
                print(f"Reservación creada con éxito. Folio: {cursor.lastrowid}")
            except sqlite3.IntegrityError:
                print("No se pudo crear la reservación: la sala/turno ya está ocupada en esa fecha.")
    except Exception as e:
        print("Error al registrar reservación:", e)

def consultar_reservaciones():
    print("\nConsultar reservaciones por fecha")
    try:
        fecha_txt = input("Fecha (MM-DD-AAAA) [Enter = hoy]: ").strip()
        if not fecha_txt:
            fecha_txt = datetime.date.today().strftime("%m-%d-%Y")
        fecha = validar_fecha_str(fecha_txt)
        if not fecha:
            print("Formato de fecha inválido.")
            return
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT R.folio, C.apellidos || ', ' || C.nombres AS cliente, S.nombre AS sala,
                       S.cupo, R.turno, R.evento
                FROM Reservaciones R
                JOIN Clientes C ON R.id_cliente = C.id
                JOIN Salas S ON R.id_sala = S.id
                WHERE R.fecha = ?
                ORDER BY S.nombre, R.turno
            """, (fecha_txt,))
            rows = cursor.fetchall()
            if not rows:
                print("No hay reservaciones para esa fecha.")
                return
            headers = ["FOLIO", "CLIENTE", "SALA", "CUPO", "TURNO", "EVENTO"]
            print(tabulate(rows, headers=headers, tablefmt="grid"))
            export = input("¿Desea exportar el reporte a JSON? (S/N): ").strip().upper()
            if export == "S":
                datos = []
                for folio, cliente, sala, cupo, turno, evento in rows:
                    datos.append({
                        "folio": folio,
                        "cliente": cliente,
                        "sala": sala,
                        "cupo": cupo,
                        "turno": turno,
                        "evento": evento,
                        "fecha": fecha_txt
                    })
                nombre_archivo = f"reservaciones_{fecha_txt.replace('-', '')}.json"
                with open(nombre_archivo, "w", encoding="utf-8") as f:
                    json.dump(datos, f, indent=2, ensure_ascii=False)
                print(f"Reporte exportado a {nombre_archivo}")
    except Exception as e:
        print("Error al consultar reservaciones:", e)

def editar_reservacion():
    print("\nEditar nombre del evento (rango de fechas)")
    try:
        inicio_txt = input("Fecha inicial (MM-DD-AAAA): ").strip()
        fin_txt = input("Fecha final (MM-DD-AAAA): ").strip()
        inicio = validar_fecha_str(inicio_txt)
        fin = validar_fecha_str(fin_txt)
        if not inicio or not fin:
            print("Formato de fecha inválido.")
            return
        if inicio > fin:
            print("El inicio no puede ser posterior al fin.")
            return
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT R.folio, R.fecha, R.evento, C.apellidos || ', ' || C.nombres AS cliente
                FROM Reservaciones R
                JOIN Clientes C ON R.id_cliente = C.id
                WHERE date(substr(R.fecha,7,4)||'-'||substr(R.fecha,1,2)||'-'||substr(R.fecha,4,2))
                      BETWEEN date(substr(?,7,4)||'-'||substr(?,1,2)||'-'||substr(?,4,2))
                          AND date(substr(?,7,4)||'-'||substr(?,1,2)||'-'||substr(?,4,2))
                ORDER BY R.fecha
            """, (inicio_txt, inicio_txt, inicio_txt, fin_txt, fin_txt, fin_txt))
            resultados = cursor.fetchall()
            if not resultados:
                print("No hay reservaciones en ese rango de fechas.")
                return
            headers = ["FOLIO", "FECHA", "EVENTO", "CLIENTE"]
            print(tabulate(resultados, headers=headers, tablefmt="grid"))
            folios_validos = {r[0] for r in resultados}
            while True:
                entrada = input("Indica el folio del evento a modificar (0 = cancelar): ").strip()
                try:
                    folio = int(entrada)
                except ValueError:
                    print("Debes ingresar un número.")
                    continue
                if folio == 0:
                    print("Operación cancelada.")
                    return
                if folio not in folios_validos:
                    print("Ese folio no pertenece al rango mostrado. Selecciona otro o 0 para cancelar.")
                    continue
                break
            while True:
                nuevo = input("Nuevo nombre del evento: ").strip()
                if nuevo and nuevo.strip():
                    break
                print("El nombre del evento no puede quedar vacío.")
            cursor.execute("UPDATE Reservaciones SET evento = ? WHERE folio = ?", (nuevo, folio))
            conn.commit()
            print("Evento actualizado con éxito.")
    except Exception as e:
        print("Error al editar reservación:", e)

def cancelar_reservacion():
    print("\nCancelar reservación (se elimina de la base de datos)")
    try:
        inicio_txt = input("Fecha inicio (MM-DD-AAAA): ").strip()
        fin_txt = input("Fecha fin (MM-DD-AAAA): ").strip()
        inicio = validar_fecha_str(inicio_txt)
        fin = validar_fecha_str(fin_txt)
        if not inicio or not fin:
            print("Formato de fecha inválido.")
            return
        if inicio > fin:
            print("La fecha inicio no puede ser posterior a la fecha fin.")
            return
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT folio, fecha, evento, C.apellidos || ', ' || C.nombres AS cliente, S.nombre AS sala
                FROM Reservaciones R
                JOIN Clientes C ON R.id_cliente = C.id
                JOIN Salas S ON R.id_sala = S.id
                WHERE date(substr(R.fecha,7,4)||'-'||substr(R.fecha,1,2)||'-'||substr(R.fecha,4,2))
                      BETWEEN date(substr(?,7,4)||'-'||substr(?,1,2)||'-'||substr(?,4,2))
                          AND date(substr(?,7,4)||'-'||substr(?,1,2)||'-'||substr(?,4,2))
                ORDER BY R.fecha
            """, (inicio_txt, inicio_txt, inicio_txt, fin_txt, fin_txt, fin_txt))
            rows = cursor.fetchall()
            if not rows:
                print("No hay reservaciones en ese rango de fechas.")
                return
            headers = ["FOLIO", "FECHA", "EVENTO", "CLIENTE", "SALA"]
            print(tabulate(rows, headers=headers, tablefmt="grid"))
            folios_validos = {r[0] for r in rows}
            while True:
                entrada = input("Folio a cancelar (0 = cancelar): ").strip()
                try:
                    folio = int(entrada)
                except ValueError:
                    print("Debe ingresar un número.")
                    continue
                if folio == 0:
                    print("Operación cancelada.")
                    return
                if folio not in folios_validos:
                    print("Folio no válido para este rango.")
                    continue
                fila = next(r for r in rows if r[0] == folio)
                fecha_res = validar_fecha_str(fila[1])
                if not fecha_res:
                    print("Formato de fecha interno inválido, operación abortada.")
                    return
                hoy = datetime.date.today()
                if fecha_res < hoy + datetime.timedelta(days=2):
                    print("No se puede cancelar con menos de 2 días de anticipación.")
                    return
                confirmar = input(f"Confirma eliminar la reservación {folio} (S/N): ").strip().upper()
                if confirmar == "S":
                    cursor.execute("DELETE FROM Reservaciones WHERE folio = ?", (folio,))
                    conn.commit()
                    print("Reservación eliminada y disponibilidad recuperada.")
                else:
                    print("Operación cancelada por el usuario.")
                return
    except Exception as e:
        print("Error al cancelar reservación:", e)

def menu():
    inicializar_db()
    while True:
        print("\n==================== MENÚ PRINCIPAL ====================")
        print("1. Registrar la reservación de una sala")
        print("2. Editar el nombre del evento de una reservación (rango de fechas)")
        print("3. Consultar las reservaciones para una fecha")
        print("4. Cancelar una reservación (rango de fechas)")
        print("5. Registrar un nuevo cliente")
        print("6. Registrar una sala")
        print("7. Salir")
        print("=======================================================")
        opcion = input("Opción: ").strip()
        if opcion == "1":
            registrar_reservacion()
        elif opcion == "2":
            editar_reservacion()
        elif opcion == "3":
            consultar_reservaciones()
        elif opcion == "4":
            cancelar_reservacion()
        elif opcion == "5":
            registrar_cliente()
        elif opcion == "6":
            registrar_sala()
        elif opcion == "7":
            confirmar = input("¿Desea salir? (S/N): ").strip().upper()
            if confirmar == "S":
                print("Saliendo. El estado está guardado en la base de datos.")
                break
            else:
                print("Regresando al menú principal.")
        else:
            print("Opción no válida. Intente nuevamente.")

if __name__ == "__main__":
    menu()
