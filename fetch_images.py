import math
from typing import Tuple
from sentinelhub import (
    SHConfig,
    CRS,
    BBox,
    DataCollection,
    DownloadRequest,
    MimeType,
    MosaickingOrder,
    SentinelHubDownloadClient,
    SentinelHubRequest,
    bbox_to_dimensions,
)
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import shutil
import time


class FetchImages:
    def __init__(
        self,
        data: pd.DataFrame,
        config: object,
        evalscript: str,
        threads: int = 5,
        size_km=50,
        resolution: int = 100,
        time_interval_size=5,
        verbose=False,
        mosaicking_order: MosaickingOrder = MosaickingOrder.LEAST_CC,
        save_dir: str = "./satelite_data",
    ):
        self.data = data
        self.config = config
        self.evalscript = evalscript
        self.threads = threads
        self.size_km = (
            size_km // 2
        )  # due to the fact that, original value represent half of box edge len
        self.resolution = resolution
        self.time_interval_size = time_interval_size
        self.verbose = verbose
        self.save_dir = save_dir
        self.mosaicking_order = mosaicking_order
        self.mapper = {}

    def fetch(self) -> None:
        list_of_requests = []
        self.mapper = {}
        for index, row in self.data.iterrows():
            time_interval = self._define_time_interval(row)
            bbox, size = self._define_bbox(row["Latitude"], row["Longitude"])
            self.mapper[bbox.geometry.bounds] = f"HELCOM_ID_{row['HELCOM_ID']}"
            request = self._get_request(
                time_interval=time_interval,
                bbox=bbox,
                size=size,
            )
            list_of_requests.append(request.download_list[0])
        print("Loading...")
        data = SentinelHubDownloadClient(config=self.config).download(
            list_of_requests, max_threads=self.threads
        )
        print(f"Done! Results save in {self.save_dir}")
        return self

    def _define_time_interval(self, row):
        return (
            row["Date_standard"] - timedelta(days=self.time_interval_size),
            row["Date_standard"] + timedelta(days=self.time_interval_size),
        )

    def _define_bbox(
        self, latitude: float, longitude: float
    ) -> Tuple[BBox, Tuple[int]]:
        km_per_degree = 111  # 1 degree = 111 km approximately

        lat_offset = self.size_km / km_per_degree
        lon_offset = lat_offset / math.cos(math.radians(latitude))

        lat_min = latitude - lat_offset
        lat_max = latitude + lat_offset
        lon_min = longitude - lon_offset
        lon_max = longitude + lon_offset

        bbox_WGS84 = [lon_min, lat_min, lon_max, lat_max]
        bbox = BBox(bbox=bbox_WGS84, crs=CRS.WGS84)
        size = bbox_to_dimensions(bbox, resolution=self.resolution)

        if self.verbose:
            print(
                "To see actual bbox go to this page http://bboxfinder.com/#0.000000,0.000000,0.000000,0.000000 and paste cords"
            )
            print(f"({lon_min}, {lat_min}, {lon_max}, {lat_max})")
        return bbox, size

    def _get_request(
        self,
        time_interval: Tuple[datetime],
        bbox: BBox,
        size: Tuple[int],
    ) -> np.array:
        request = SentinelHubRequest(
            evalscript=self.evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L1C.define_from(
                        "s2l1c", service_url=self.config.sh_base_url
                    ),
                    time_interval=time_interval,
                    mosaicking_order=self.mosaicking_order,
                )
            ],
            responses=[SentinelHubRequest.output_response("default", MimeType.PNG)],
            bbox=bbox,
            size=size,
            config=self.config,
            data_folder=self.save_dir,
        )
        return request

    def rename_request_png_based_on_json(self):
        for subdir, dirs, files in os.walk(self.save_dir):
            if (
                "request.json" in files and "response.png" in files
            ):  # Check both files exist
                json_file_path = os.path.join(subdir, "request.json")
                png_file_path = os.path.join(subdir, "response.png")

                print(f"Processing JSON file: {json_file_path}")
                try:
                    # Open and read the JSON file
                    with open(json_file_path, "r") as json_file:
                        data = json.load(json_file)
                        # Extract the relevant value (e.g., bbox from JSON)
                        value = tuple(
                            data["request"]["payload"]["input"]["bounds"]["bbox"]
                        )

                        if value and value in self.mapper:
                            # Get the new file name from the mapping
                            new_file_name = str(self.mapper[value])
                            new_png_file_path = os.path.join(
                                subdir, f"{new_file_name}.png"
                            )

                            # Retry logic to rename the file if it's locked
                            retries = 3
                            for attempt in range(retries):
                                try:
                                    shutil.move(
                                        png_file_path, new_png_file_path
                                    )  # Rename the PNG file
                                    print(
                                        f"Renamed {png_file_path} to {new_png_file_path}"
                                    )
                                    break  # Exit loop if successful
                                except PermissionError as e:
                                    print(f"Attempt {attempt + 1} failed: {e}")
                                    if attempt < retries - 1:
                                        time.sleep(1)  # Wait before retrying
                                    else:
                                        print(
                                            f"Failed to rename {png_file_path} after {retries} attempts."
                                        )
                                        raise  # Re-raise the exception if all attempts fail
                except Exception as e:
                    print(f"Error processing {json_file_path}: {e}")
