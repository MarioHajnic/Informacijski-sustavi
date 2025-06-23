print("--- Flask application script is starting ---")

from flask import Flask, request, make_response, jsonify, render_template
from pony import orm
from datetime import datetime
from collections import defaultdict
from itertools import groupby

DB = orm.Database()
app = Flask(__name__)

class Zaposlenik(DB.Entity):
    id = orm.PrimaryKey(int, auto=True)
    ime = orm.Required(str)
    prezime = orm.Required(str)
    datum_rodjenja = orm.Required(datetime)
    godine = orm.Required(int)
    djeca = orm.Required(int)
    bracni_status = orm.Required(str)
    adresa_stanovanja = orm.Required(str)
    telefon = orm.Required(str)
    email = orm.Required(str)
    radni_detalji = orm.Optional('RadniDetalji')

class RadniDetalji(DB.Entity):
    id = orm.PrimaryKey(int, auto=True)
    zaposlenik = orm.Required(Zaposlenik)
    godine_radnog_staza = orm.Required(int)
    strucna_sprema = orm.Required(str)
    placa = orm.Required(float)
    broj_dana_godisnjeg = orm.Required(int)
    jezik = orm.Required(str)
    datum_zaposlenja = orm.Required(datetime)
    datum_otkaza = orm.Optional(datetime)

DB.bind(provider="sqlite", filename="teamtrack.sqlite", create_db=True)
DB.generate_mapping(create_tables=True)


def formatiraj_datum(datum):
    return datum.strftime('%Y-%m-%d') if datum else None


@orm.db_session
def add_zaposlenik(json_request):
    try:
        datum_rodjenja_str = json_request.get('datum_rodjenja')
        datum_zaposlenja_str = json_request.get('datum_zaposlenja')
        
        if not datum_rodjenja_str:
            raise ValueError("Datum rođenja je obavezan.")
        if not datum_zaposlenja_str:
            raise ValueError("Datum zaposlenja je obavezan.")

        zaposlenik_data = {
            "ime": json_request["ime"],
            "prezime": json_request["prezime"],
            "datum_rodjenja": datetime.fromisoformat(datum_rodjenja_str),
            "godine": int(json_request["godine"]),
            "djeca": int(json_request["djeca"]),
            "bracni_status": json_request["bracni_status"],
            "adresa_stanovanja": json_request["adresa_stanovanja"],
            "telefon": json_request["telefon"],
            "email": json_request["email"]
        }
        
        radni_detalji_data = {
            "godine_radnog_staza": int(json_request["godine_radnog_staza"]),
            "strucna_sprema": json_request["strucna_sprema"],
            "placa": float(json_request["placa"]),
            "broj_dana_godisnjeg": int(json_request["broj_dana_godisnjeg"]),
            "jezik": json_request["jezik"],
            "datum_zaposlenja": datetime.fromisoformat(datum_zaposlenja_str)
        }

        datum_otkaza_str = json_request.get("datum_otkaza")
        if datum_otkaza_str:
            radni_detalji_data["datum_otkaza"] = datetime.fromisoformat(datum_otkaza_str)

        zaposlenik = Zaposlenik(**zaposlenik_data)
        RadniDetalji(zaposlenik=zaposlenik, **radni_detalji_data)
        return {"response": "Success"}
    except Exception as e:
        print(f"DEBUG add_zaposlenik error: {e}")
        return {"response": "Fail", "error": str(e)}

@orm.db_session
def get_zaposlenici():
    try:
        db_query = orm.select(z for z in Zaposlenik)
        results_list = []
        for z in db_query:
            z_dict = z.to_dict()
            z_dict['datum_rodjenja'] = formatiraj_datum(z_dict['datum_rodjenja'])
            
            if z.radni_detalji:
                rd_dict = z.radni_detalji.to_dict()
                rd_dict['datum_zaposlenja'] = formatiraj_datum(rd_dict['datum_zaposlenja'])
                rd_dict['datum_otkaza'] = formatiraj_datum(rd_dict['datum_otkaza'])
                z_dict['radni_detalji'] = rd_dict
            else:
                z_dict['radni_detalji'] = None
            results_list.append(z_dict)
        print(f"DEBUG get_zaposlenici data: {results_list}")
        return {"response": "Success", "data": results_list}
    except Exception as e:
        print(f"DEBUG get_zaposlenici error: {e}")
        return {"response": "Fail", "error": str(e)}

@orm.db_session
def get_zaposlenik_by_id(zaposlenik_id):
    try:
        zaposlenik = Zaposlenik[zaposlenik_id]
        result = zaposlenik.to_dict()
        result['datum_rodjenja'] = formatiraj_datum(result['datum_rodjenja'])

        if zaposlenik.radni_detalji:
            rd_dict = zaposlenik.radni_detalji.to_dict()
            rd_dict['datum_zaposlenja'] = formatiraj_datum(rd_dict['datum_zaposlenja'])
            rd_dict['datum_otkaza'] = formatiraj_datum(rd_dict['datum_otkaza'])
            result['radni_detalji'] = rd_dict
        else:
            result['radni_detalji'] = None
        print(f"DEBUG get_zaposlenik_by_id data for {zaposlenik_id}: {result}")
        return {"response": "Success", "data": result}
    except Exception as e:
        print(f"DEBUG get_zaposlenik_by_id error for {zaposlenik_id}: {e}")
        return {"response": "Fail", "error": str(e)}

@orm.db_session
def patch_zaposlenik(zaposlenik_id, json_request):
    try:
        to_update_zaposlenik = Zaposlenik[zaposlenik_id]
        to_update_radni_detalji = to_update_zaposlenik.radni_detalji

        for key, value in json_request.items():
            if hasattr(to_update_zaposlenik, key):
                if key == 'datum_rodjenja':
                    if value:
                        to_update_zaposlenik.datum_rodjenja = datetime.fromisoformat(value)
                elif key in ['godine', 'djeca']:
                    if value:
                        setattr(to_update_zaposlenik, key, int(value))
                else:
                    setattr(to_update_zaposlenik, key, value)
            elif to_update_radni_detalji and hasattr(to_update_radni_detalji, key):
                if key in ['datum_zaposlenja', 'datum_otkaza']:
                    if value:
                        setattr(to_update_radni_detalji, key, datetime.fromisoformat(value))
                    else:
                        setattr(to_update_radni_detalji, key, None)
                elif key in ['godine_radnog_staza', 'broj_dana_godisnjeg']:
                    if value:
                        setattr(to_update_radni_detalji, key, int(value))
                elif key == 'placa':
                    if value:
                        setattr(to_update_radni_detalji, key, float(value))
                else:
                    setattr(to_update_radni_detalji, key, value)
        return {"response": "Success"}
    except Exception as e:
        print(f"DEBUG patch_zaposlenik error for {zaposlenik_id}: {e}")
        return {"response": "Fail", "error": str(e)}

@orm.db_session
def delete_zaposlenik(zaposlenik_id):
    try:
        to_delete = Zaposlenik[zaposlenik_id]
        if to_delete.radni_detalji:
            to_delete.radni_detalji.delete()
        to_delete.delete()
        return {"response": "Success"}
    except Exception as e:
        print(f"DEBUG delete_zaposlenik error for {zaposlenik_id}: {e}")
        return {"response": "Fail", "error": str(e)}

@orm.db_session
def get_salary_by_children_data():
    try:
        print("DEBUG: Starting get_salary_by_children_data")
        
        total_employees = orm.count(z for z in Zaposlenik)
        print(f"DEBUG: Total employees in database: {total_employees}")
        
        total_work_details = orm.count(rd for rd in RadniDetalji)
        print(f"DEBUG: Total work details in database: {total_work_details}")
        
        employees = list(orm.select(z for z in Zaposlenik))
        print(f"DEBUG: Retrieved {len(employees)} employees")
        
        employees_data = []
        
        for i, zaposlenik in enumerate(employees):
            try:
                print(f"DEBUG: Processing employee {i+1}: ID={zaposlenik.id}, Name={zaposlenik.ime} {zaposlenik.prezime}")
                print(f"DEBUG: Employee children: {zaposlenik.djeca}")
                
                if hasattr(zaposlenik, 'radni_detalji') and zaposlenik.radni_detalji:
                    print(f"DEBUG: Employee has work details")
                    print(f"DEBUG: Work details ID: {zaposlenik.radni_detalji.id}")
                    print(f"DEBUG: Salary: {zaposlenik.radni_detalji.placa}")
                    
                    djeca = zaposlenik.djeca
                    placa = zaposlenik.radni_detalji.placa
                    
                    print(f"DEBUG: Creating tuple: ({djeca}, {placa})")
                    employees_data.append((djeca, placa))
                    print(f"DEBUG: Successfully added tuple. Total tuples so far: {len(employees_data)}")
                else:
                    print(f"DEBUG: Employee has NO work details")
                    
            except Exception as inner_e:
                print(f"DEBUG: Error processing employee {i+1} (ID: {zaposlenik.id if hasattr(zaposlenik, 'id') else 'unknown'}): {inner_e}")
                import traceback
                print(f"DEBUG: Inner traceback: {traceback.format_exc()}")
                continue
        
        print(f"DEBUG: Final employees_data length: {len(employees_data)}")
        print(f"DEBUG: Final employees_data content: {employees_data}")
        
        if not employees_data:
            print("DEBUG: No valid employee data found")
            return {"response": "Success", "data": []}
        
        print("DEBUG: Starting grouping process")
        grouped_data = defaultdict(lambda: {'total_salary': 0, 'count': 0})
        
        for i, data_tuple in enumerate(employees_data):
            try:
                print(f"DEBUG: Processing tuple {i+1}: {data_tuple}")
                print(f"DEBUG: Tuple length: {len(data_tuple)}")
                print(f"DEBUG: Tuple type: {type(data_tuple)}")
                
                if len(data_tuple) != 2:
                    print(f"DEBUG: ERROR - Tuple has {len(data_tuple)} elements instead of 2!")
                    continue
                    
                djeca, placa = data_tuple
                print(f"DEBUG: Extracted - djeca: {djeca}, placa: {placa}")
                
                if djeca is not None and placa is not None:
                    grouped_data[djeca]['total_salary'] += placa
                    grouped_data[djeca]['count'] += 1
                    print(f"DEBUG: Added to group {djeca}")
                else:
                    print(f"DEBUG: Skipped due to None values - djeca: {djeca}, placa: {placa}")
                    
            except Exception as tuple_error:
                print(f"DEBUG: Error processing tuple {i+1}: {tuple_error}")
                import traceback
                print(f"DEBUG: Tuple error traceback: {traceback.format_exc()}")
                continue
        
        print(f"DEBUG: Grouped data: {dict(grouped_data)}")
        
        chart_data = []
        for djeca, values in sorted(grouped_data.items()):
            if values['count'] > 0:
                average_salary = values['total_salary'] / values['count']
                chart_data.append({"broj_djece": djeca, "prosjecna_placa": average_salary})
        
        print(f"DEBUG: Final chart_data: {chart_data}")
        return {"response": "Success", "data": chart_data}
        
    except Exception as e:
        print(f"DEBUG: Main function error: {e}")
        import traceback
        print(f"DEBUG: Main traceback: {traceback.format_exc()}")
        return {"response": "Fail", "error": str(e)}

@orm.db_session
def filter_zaposlenici(filter_params):
    try:
        query = orm.select(z for z in Zaposlenik)
        
        if filter_params.get('has_children'):
            if filter_params['has_children'] == 'yes':
                query = query.filter(lambda z: z.djeca > 0)
            elif filter_params['has_children'] == 'no':
                query = query.filter(lambda z: z.djeca == 0)
        
        if filter_params.get('bracni_status'):
            query = query.filter(lambda z: z.bracni_status == filter_params['bracni_status'])
            
        if filter_params.get('strucna_sprema'):
            query = query.filter(lambda z: z.radni_detalji is not None and z.radni_detalji.strucna_sprema == filter_params['strucna_sprema'])

        results_list = []
        for z in query:
            z_dict = z.to_dict()
            z_dict['datum_rodjenja'] = formatiraj_datum(z_dict['datum_rodjenja'])
            if z.radni_detalji:
                rd_dict = z.radni_detalji.to_dict()
                rd_dict['datum_zaposlenja'] = formatiraj_datum(rd_dict['datum_zaposlenja'])
                rd_dict['datum_otkaza'] = formatiraj_datum(rd_dict['datum_otkaza'])
                z_dict['radni_detalji'] = rd_dict
            else:
                z_dict['radni_detalji'] = None
            results_list.append(z_dict)
        print(f"DEBUG filter_zaposlenici data: {results_list}")
        return {"response": "Success", "data": results_list}
    except Exception as e:
        print(f"DEBUG filter_zaposlenici error: {e}")
        return {"response": "Fail", "error": str(e)}


@app.route("/", methods=["GET"])
def home():
    return make_response(render_template("index.html"), 200)

@app.route("/dodaj_zaposlenika", methods=["POST", "GET"])
def dodaj_zaposlenika_route():
    if request.method == "POST":
        try:
            json_request = {}
            for key, value in request.form.items():
                json_request[key] = value if value else None
        except Exception as e:
            response = {"response": str(e)}
            return make_response(jsonify(response), 400)
        
        response = add_zaposlenik(json_request)
        if response["response"] == "Success":
            return make_response(render_template("dodaj_zaposlenika.html", message="Zaposlenik uspješno dodan!"), 200)
        return make_response(jsonify(response), 400)
    else:
        return make_response(render_template("dodaj_zaposlenika.html"), 200)

@app.route("/uredi_zaposlenike", methods=["GET"])
def uredi_zaposlenike_route():
    response = get_zaposlenici()
    if response["response"] == "Success":
        return make_response(render_template("uredi_zaposlenike.html", data=response["data"]), 200)
    return make_response(jsonify(response), 400)

@app.route("/zaposlenik/<int:zaposlenik_id>", methods=["DELETE"])
def obrisi_zaposlenika_route(zaposlenik_id):
    response = delete_zaposlenik(zaposlenik_id)
    if response["response"] == "Success":
        return make_response(jsonify(response), 200)
    return make_response(jsonify(response), 400)

@app.route("/zaposlenik/<int:zaposlenik_id>", methods=["GET", "POST"])
def izmjeni_zaposlenika_route(zaposlenik_id):
    if request.method == "GET":
        response = get_zaposlenik_by_id(zaposlenik_id)
        if response["response"] == "Success":
            return make_response(render_template("izmjeni_zaposlenika.html", zaposlenik=response["data"]), 200)
        return make_response(jsonify(response), 400)
    elif request.method == "POST":
        try:
            json_request = {}
            for key, value in request.form.items():
                json_request[key] = value if value else None
        except Exception as e:
            return make_response(jsonify({"response": str(e)}), 400)
        
        response = patch_zaposlenik(zaposlenik_id, json_request)
        if response["response"] == "Success":
            updated_zaposlenik = get_zaposlenik_by_id(zaposlenik_id)["data"]
            return make_response(render_template("izmjeni_zaposlenika.html", zaposlenik=updated_zaposlenik, message="Podaci uspješno ažurirani!"), 200)
        return make_response(jsonify(response), 400)

@app.route("/vizualizacija_podataka", methods=["GET"])
def vizualizacija_podataka_route():
    try:
        chart_data_response = get_salary_by_children_data()
        if chart_data_response["response"] == "Success":
            chart_data = chart_data_response["data"]
            broj_djece = [item["broj_djece"] for item in chart_data]
            prosjecne_place = [item["prosjecna_placa"] for item in chart_data]
            return make_response(render_template("vizualizacija_podataka.html", broj_djece=broj_djece, prosjecne_place=prosjecne_place), 200)
        return make_response(jsonify(chart_data_response), 400)
    except Exception as e:
        error_response = {"response": "Error", "error_message": str(e)}
        print(f"DEBUG vizualizacija_podataka_route error: {e}")
        return make_response(jsonify(error_response), 500)

@app.route("/filtriranje_podataka", methods=["GET", "POST"])
def filtriranje_podataka_route():
    if request.method == "POST":
        filter_params = {}
        if request.form.get('has_children'):
            filter_params['has_children'] = request.form['has_children']
        if request.form.get('bracni_status'):
            filter_params['bracni_status'] = request.form['bracni_status']
        if request.form.get('strucna_sprema'):
            filter_params['strucna_sprema'] = request.form['strucna_sprema']
        
        response = filter_zaposlenici(filter_params)
        if response["response"] == "Success":
            return make_response(render_template("filtriranje_podataka.html", data=response["data"], filter_params=filter_params), 200)
        return make_response(jsonify(response), 400)
    else:
        response = get_zaposlenici()
        if response["response"] == "Success":
            return make_response(render_template("filtriranje_podataka.html", data=response["data"]), 200)
        return make_response(jsonify(response), 400)

if __name__ == "__main__":
    app.run(port=8080, host='0.0.0.0', debug=True)
