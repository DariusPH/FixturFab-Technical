from enum import Enum
from fastapi import FastAPI, UploadFile
from io import BytesIO
from pydantic import BaseModel
from typing import Union, List
import numpy as np
import pandas as pd


class Sides(Enum):
    """ The possible options for the side of the PCB to be tested. """
    top = 'Top'
    bottom = 'Bottom'


class Types(Enum):
    """ The possible types of testing to be performed. """
    pressre = 'Pressure Pin'
    locating = 'Locating Pin'
    smd = 'SMD'
    hole = 'Through Hole'


class Test_Point(BaseModel):
    """ Test points on the board, net and hole_size are optional. """
    net: Union[int, None] = None
    name: str
    x_coord: float
    y_coord: float
    side: Sides
    type: Types
    hole_size: Union[float, None] = None


class PCB(BaseModel):
    """ The board itself, and test points are attached to the PCB model.
    It was ambiguous if height and width should be int or float,
    float seemed more appropriate as it is more specific."""
    height: float
    height_notes: Union[str, None]
    width: float
    width_notes: Union[str, None]
    thickness: float
    thickness_notes: Union[str, None]
    test_points: List[Test_Point] = []


app = FastAPI()


@app.get("/")
async def root():
    """ This project didn't feel like something that should run at root. Many
    API's I've used just return their host if you hit root, so I've done
    that here. Well, not my host, but yours."""
    return "https://fixturfab.com/"


@app.post("/upload_pcb/")
async def upload_PCB(file: UploadFile):
    """ An endpoint that a user can upload an excel spreadsheet to to add it
    to convet it into a json format. A preefilled template can be found here:
    https://docs.google.com/spreadsheets/d/1qiXn-cy2ksJ9o5uTX6tQJOr8C2j0VUL_8TejX4TTofk/edit#gid=647071454
    """

    xlsx = BytesIO(file.file.read())  # Convert to a bit stream for Pandas

    PCB_df = pd.read_excel(io=xlsx, sheet_name="PCB Specification",
                           index_col=0, keep_default_na=False).transpose()
    test_point_df = pd.read_excel(io=xlsx, sheet_name="Test Point List",
                                  keep_default_na=False)

    # Removes the "(mm)" and any trailing whitespace to make it easier to call.
    PCB_df.columns = [x.split(" ")[0].title() for x in PCB_df.columns.values]

    # There is certainly a cleaner way to do this but I ran out of time.
    Current_PCB = PCB(
        height=PCB_df["Height"]["Value"],
        height_notes=PCB_df["Height"]["Notes"],
        width=PCB_df["Width"]["Value"],
        width_notes=PCB_df["Width"]["Notes"],
        thickness=PCB_df["Thickness"]["Value"],
        thickness_notes=PCB_df["Thickness"]["Notes"]
    )

    # This code fixes up a few things so the data is the correct datatype.
    # X, Y and Hole Size could probably be a function.
    # I felt changing these line to be PEP8 compliant made them less readable.
    test_point_df["Net"] = test_point_df["Net"].apply(lambda x: x.lstrip("NET"))
    test_point_df["X Coord"] = test_point_df["X Coord"].apply(lambda x: x.rstrip("mm"))
    test_point_df["Y Coord"] = test_point_df["Y Coord"].apply(lambda x: x.rstrip("mm"))
    test_point_df["Side"] = test_point_df["Side"].apply(lambda x: Sides(x))
    test_point_df["Type"] = test_point_df["Type"].apply(lambda x: Types(x))
    test_point_df["Hole Size"] = test_point_df["Hole Size"].apply(lambda x: x.rstrip("mm"))

    # Changes any empty strings into None
    test_point_df = test_point_df.apply(np.vectorize(lambda x: x if x else None))

    # Converts names in file to Pydantics Model names.
    test_point_df.columns = [x.replace(" ", "_").lower() for x in test_point_df.columns.values]

    # Changes each row into a testpoint, then adds it to the PCB Model
    for iter, row in test_point_df.iterrows():
        point = row.to_dict()
        p = Test_Point(**point)
        Current_PCB.test_points.append(p)  # Adds point to PCB

    return Current_PCB
