# AI Project: `Geohilfe AI`
<hr></hr>

### Introduction:
The following codebase is the most current (as of 19 July 2023) version of `GeoHilfe AI`. Geohilfe aims to assist emergency services operators in locating patients by listening in to live patient calls. Geohilfe extracts keywords from the conversation (places, landmarks, streets) and displays them for the operator to select. Operators can choose which keywords are relevant and these are sent to the AI model. Using the selected keywords, a similarity function computes scores on where the patient is most likely located. The scores are sent back to the operator along with their respective grid information. These scores and grids are displayed for the operator to see.  

### Dataset
The `Geohilfe Locations` dataset used can be found under `app/geohile_data_aws_v2.csv`. The dataset was created using `AWS Location (Esri)` services and only covers the town of `Meersburg`. It covers a 4.5km x 6.0km area. Each row in the dataset signifies one (1) 300x300 meter grid and its associated establishments, streets, and landmarks for a total of 300 data points.

### Project Requirements 
For complete list of dependencies, refer to requirements.txt

```bash
- Python3.10.9
- git
- Docker
```

### Project Structure

```bash
Geohilfe AI (version 2.2)
├── app
│   └── BlueConeCheck.py
│   └── geo_database.py
│   └── geohilfe_data_aws_v1.csv
│   └── geohilfe_data_aws_v2.csv
│   └── KeyWordExtraction.py
│   └── model_api.py
│   └── SimilarityModel.py
├── models
│   └── RF_Model_V1.pkl
├── docker-compose.yaml
├── Dockerfile
├── Dockerfile_local
├── requirements.txt
├── geohilfe_data_v1.csv
├── initial_database.csv
└── requirements.txt
```
    
### Using Geohilfe AI via FastAPI (local deployment)
Install all dependencies before proceeding.

The FastAPI server can be run using the following command. The `--port` parameter can be changed to what is available to the user.

```bash
cd ai
uvicorn app.model_api:app --host 0.0.0.0 --port 8080
```

### Using Geohilfe AI as a Docker service (local deployment)

There are two (2) Dockerfiles in the folder, one is used for local deployment and the other for a cloud build. Use `Dockerfile_local`for a local set-up.

- `Step1`: Build the Docker image
```bash
docker build -f Dockerfile_local -t geohilfe-ai
```

- `Step 2`: Run the Docker image once build has completed
```bash
docker run -d -p 8080:8080 --name ai-test geohilfe-ai
```

- `Step 3`: Check if the container is running in the background
```bash
docker ps
```

### Interacting with Geohilfe AI

The Geohilfe AI, once deployed, can be interacted with using JSON Requests. Each of these requests are outlined below along with their appropriate JSON response.

- GET `/healthz`: A simple health check to verify if Geohilfe AI is running.

`Response`
```bash
{
    "status": "OK"
}
```

- POST `/bluecone`: Sends the Blue Signal Cone information to the AI model. The request contains all needed information to emulate the Blue Signal Cone. This also creates a subset of grids that are encompassed by the Blue Signal Cone based on the Geohilfe Locations dataset. This grids subset will be used by the Similarity Function. The response gives two (2) key pieces of information: (1) coordinates for the visualization of the Blue Signal Cone in the frontend, and (2) the relevant grids and coordinates needed to visualize the bounding boxes.

`Request`
```bash
{
    "cone_origin": [47.701755, 9.271295],
    "cone_radius": 1000,
    "cone_angle": 90,
    "cone_direction": 90 
}
```

`Response`
```bash
{
    "bluecone_points": [
        [
            47.692801,
            9.284686
        ],
        [
            47.70325975749226,
            9.260359486191872
        ],
        [{
    "keywords": [
        "friedrichshafen",
        "gas station",
        "Rewe"
    ]
}[
        {
            "grid_number": 32,
            "northeast": [
                47.70525050146264,
                9.260195365125734
            ],
            "southeast": [
                47.7025522154637,
                9.260195365125734
            ],
            "southwest": [
                47.7025522154637,
                9.256197381082037
            ],
            "northwest": [
                47.70525050146264,
                9.256197381082037
            ]
        },
.
.
.
}
```

- POST `/extract`: Extract keywords from the transcription text sent from the Speech-to-Text feature. Returns a list of keywords the user can select.

`Request`
```bash
{
    "text": "I am in friedrichshafen and I see a gas station 200 meters from me and there is a Rewe 20 feet from me"
}
```

`Response`
```bash
{
    "keywords": [
        "friedrichshafen",
        "gas station",
        "Rewe"
    ]
}
```

- POST `/similarity`: User-selected keywords are cross-referenced with key terms from each grid (streets, landmarks, establishments). The AI returns a list of all the grid information in decreasing order based on similarity scores.

`Request`
```bash
{
    "keywords" : ["Hotel", "Lodging", "Medical Clinic", "Parking", "Restaurant", "DaisendorferStraße", "Allmendweg", "Dr.-Zimmermann-Straße", "Zum Letzten Heller", "Dr. med. Reinhold Ast", "Dr. med. Wolfgang Zifreund", "Alanya Pizzeria Kebap Haus"]
}
```

`Response`
```bash
[
    {
        "grid_number": "50",
        "grid_coordinate": [
            9.270187333993979,
            47.7012029326245
        ],
        "similarity_score": "0.7288823878065065"
    },
.
.
.
]
```
docker run --rm -d -p 8000:80 ai-run-image
```