import os
import json
import pandas as pd
import data
from model import AppModel
from flask import Flask, Response, request, render_template, jsonify, send_from_directory

app = Flask(__name__)
app.debug = True

#appmodel will keep track of application state.
appmodel = AppModel()

def validate_file(path, fname):
    #return true if the file is mass spec data generated by this program.
    if fname.split(".")[-1]=="msd":
        return True

    #else, check if the file can be read as a raw data file from extrel
    else:
        try:
            data.read_extrel(path+"/"+fname)
            return True
        except:
            return False

#Page routes
@app.route("/", methods=["GET"])
def upload_page():
    """ return homepage [file upload] """
    return render_template("upload.html")

@app.route("/explore", methods=["GET"])
def explore_page():
    """ returns the exploratory analysis page """
    path = appmodel.datafolder
    filelist = os.listdir(path) if path else []
    return render_template("explore.html", filelist = filelist)

@app.route("/analyze", methods=["GET"])
def analyze_page():
    """ returns the analysis and results page """
    return render_template("analyze.html")


#AJAX API Routes - Actions
@app.route("/upload-folder", methods=["GET"])
def upload():
    """ returns a list of files in the target folder. """
    path = request.args["path"]
    appmodel.datafolder = path
    try:
        return Response(json.dumps(os.listdir(path)), mimetype="application/json")
    except FileNotFoundError:
        return Response("FileNotFoundError", status=404)

@app.route("/transform", methods=["POST"])
def transform():
    """ take data from extrel and save in an easy-to-parse format. """
    inpath = request.form["inpath"]
    outpath = request.form["outpath"]
    appmodel.transfolder = outpath
    infiles = os.listdir(inpath)
    #convert all the data and re-save using the ms
    for infile in infiles:
        print(inpath+"/"+infile)
        exposure_data = data.read_extrel(inpath+"/"+infile)
        outfile = infile.replace(".txt", ".msd")
        exposure_data.to_csv(outpath+"/"+outfile, index_label="index")
    return Response("saved", status=200)

@app.route("/run", methods=["POST"])
def run_analysis():
    outpath = request["outpath"]
    #convert amu's to ints
    amus = request["amus"]
    for i in range(len(amulist)):
        amus[i] = int(amus[i])

    bgstart, bgend = int(request["bgrange"][0]), int(request["bgrange"][1]),
    ibeam  = request["beamcurrent"]
    texp   = request["exposuretime"]

    results = analyze(inpath, bgstart, bgend, amus)

    return jsonify(list)

#AJAX API routes - application state read/write
@app.route("/data", methods=["GET"])
def get_inten_data():
    """ Handles request for amu data [primarily for graphing] """
    #get file information
    folder = appmodel.transfolder if appmodel.transfolder else appmodel.infolder
    file = request["filename"]
    ext = file.split('.')[-1]
    path = folder+"/"+file

    #decide which parser to use based on the file extention
    parser = data.read_extrel if ext==".txt" else data.read_msd

    #extract data
    amu_data = {}
    ms_data = parser(path)
    for amu in request["amus"]:
        amu_data[amu] = ms_data["amu"]

    return jsonify(amu_data)


@app.route("/amu", methods=["GET","POST"])
def update_amus():
    """ The user can select a list of AMUs. Maintain a list of selected amus
    so that if the user changes pages they can keep their list. """
    if request.method =="GET":
        return jsonify(appmodel.amus)

    elif request.method == "POST":
        op = request.form["operation"]
        value = request.form["amu"]
        if op == "add":
            if not value in appmodel.amus:
                appmodel.amus.append(int(value))

        elif op == "delete":
            print("DELETE")
            value = int(value)
            if value in appmodel.amus:
                i = appmodel.amus.index(value)
                del appmodel.amus[i]

        return Response("success", status=200)

@app.route("/settings", methods=["GET", "POST"])
def analysis_settings():
    if request.method=="GET":
        return jsonify(appmodel.analysis_params)

    elif request.method=="POST":
        params = request.form
        try:
            for param_name in params.keys():
                appmodel[param] = param
            return Response("success", status=200)

        except KeyError:
            return Response("error - setting not found - operation aborted", status=404)

@app.route("/inten", methods=["GET"])
def intensities():
    """ given a file path and amu value, fetch the intensities for that amu """
    filename = request.args["file"]
    amu  = int(request.args["amu"])

    if filename == appmodel.open_file_name:
        file = appmodel.open_file

    else:
        path = appmodel.datafolder+"/"+filename
        file = data.read_extrel(path)
        appmodel.open_file = file
        appmodel.open_file_name = filename

    return jsonify({"amus":file.loc[amu].tolist(), "scans":file.columns.tolist()})


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                          'favicon.ico',mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run()
