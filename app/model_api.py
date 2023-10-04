#from pycaret.classification import load_model, predict_model
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
#from flask import Flask, request

from ast import literal_eval
import json
import pandas as pd

print('loading dependencies...')
import app.KeyWordExtraction as kwe
import app.SimilarityModel as sm
import app.BlueConeCheck as bcc

# Create the app, added CORS but this is unsecure since it allows all origins
app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sw_nltk = None
qa_model = None
nlp = None
sample_database = None

cone_origin = None
cone_radius_m = None
cone_angle = None
cone_direction = None
grid_cells_subset = None

server_status = "loading"

# TODO: try and make a cleaner version using a class that can be passed
"""class KWDeps():
    def __init__(self, name):
        self.name = name
        self.sw_nltk = None"""

# Loading needed dependencies
@app.on_event("startup")
async def startup_event():
    global nlp
    global server_status
    # This code will run when the FastAPI server starts.
    # You can put your setup code here.

    sw_nltk, qa_model = kwe.load_libraries()
    nlp, _ = sm.sm_init()
    server_status = "ok"
    print("Server has started")


# Health check to verify if app is running 
@app.get("/health")
def health_check():
    global server_status

    return {"status": "ok"}

# Blue Signal Cone processing
# Once a call is accepted, the "answer call" button should send the blue cone info
@app.post("/bluecone")
async def process_bluecone(request: Request):
    global sample_database
    query_data = await request.json()

    # a new blue cone usually means a new subset is needed, reset the grid_cells subset
    grid_cells_subset = None

    cone_origin = query_data['cone_origin']
    cone_radius_m = query_data['cone_radius']
    cone_angle = query_data['cone_angle']
    cone_direction = query_data['cone_direction']

    filename = 'app/geohilfe_data_aws_v2.csv'
    grid_cells = pd.read_csv(filename, sep='\t', converters={"northeast": literal_eval, "southwest": literal_eval, 
                                                        "raw_data": literal_eval, "keywords": literal_eval, "addresses": literal_eval,
                                                        "landmarks": literal_eval, "subregion": literal_eval, "streets": literal_eval,}).iloc[:, 1:]
    
    # cone_origin is a list, send it as a tuple
    cone_grid = bcc.find_bc_cell(grid_cells, tuple(cone_origin))

    # find the subset of grid_cells to be used
    grid_cells_idx = bcc.get_grids_subset(grid_cells, tuple(cone_origin), cone_radius_m, cone_angle, cone_direction)
    grid_cells_subset = grid_cells.loc[grid_cells_idx]
    sample_database = grid_cells_subset

    p1 = cone_origin
    p2, p3 = bcc.get_cone_segments(cone_origin, cone_radius_m, cone_angle, cone_direction)

    p1 = [float(i) for i in p1]
    p2 = [float(i) for i in p2]
    p3 = [float(i) for i in p3]

    response = {}
    response["bluecone_points"] = [p1, p2, p3]
    response["grids"] = bcc.get_bbox_subset(grid_cells_subset)

    return JSONResponse(content=response)

# Define keyword extraction method
@app.post('/extract')
async def get_query(request: Request):
    query_data = await request.json()
    text = query_data['text']
    print(text)

    prediction = kwe.extract_keywords_from_sentence(text, sw_nltk, qa_model)

    # TODO: before returning, check for duplicate keywords?
    response = {
        'keywords': prediction
    }

    return JSONResponse(content=response)

# Define the Similarity Function
@app.post('/similarity')
async def check_keywords(request: Request):
    global sample_database

    # This logic prevents similarity from running without the blue cone data
    if sample_database is None:
        return JSONResponse(content={"message": "bluecone info not loaded"}, status_code=400)
    
    query_data = await request.json()
    keywords = query_data['keywords']

    # TODO: change how to connect or pass the database, currently we are using a .csv file
    grid_no, grid_coors, sim_scores = sm.user_keyword_handler(keywords, nlp, sample_database)

    response = []
    for entry in range(len(grid_no)):
        stage_dict = {
                        'grid_number': grid_no[entry],
                        'grid_coordinate': grid_coors[entry],
                        'similarity_score': str(sim_scores[entry])
                     }
        response.append(stage_dict)

    return JSONResponse(content=response)

# Define a reset for the AI model
# Once a call is ended, the reset function should be called so it can handle new blue cone data from another call
@app.post("/reset")
async def reset_database():
    global sample_database
    sample_database = None

    return {"status": "call ended, blue cone info unloaded - database reset"}
