import time
import tempfile
import requests
import laspy
import numpy as np

API_KEY = "413575e5-3b76-4f15-94fe-a46304de7e2a"

MAP_SHEET = "M3342B4"

EXEC_URL = (
    "https://avoin-paikkatieto.maanmittauslaitos.fi/"
    "tiedostopalvelu/ogcproc/v1/processes/"
    "laserkeilausaineisto_05_karttalehti/execution"
)

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}




    
def start_job():
    payload = {
        "id": "laserkeilausaineisto_05_karttalehti",
        "inputs": {
            "mapSheetInput": [MAP_SHEET],
            "fileFormatInput": "LAZ",
            "dataSetInput": "Uusin" 
            #Vaihtoehdot:
        #        "enum": [
          #"05p_2008-2019",
          #"05p_2020-",
          #"Uusin"
       # ]
        }
    }

    r = requests.post(
        EXEC_URL,
        json=payload,
        headers=HEADERS,
        auth=(API_KEY, "")
    )

    r.raise_for_status()
    data = r.json()

    job_url = data["links"][0]["href"]
    print("Job käynnistetty:", job_url)

    return job_url


def poll_job(job_url):
    while True:
        r = requests.get(job_url, auth=(API_KEY, ""))
        r.raise_for_status()
        data = r.json()

        print("Status:", data["status"], "Progress:", data.get("progress"))

        if data["status"] in ["successful", "succeeded", "finished"]:
            return job_url  # palauta URL, ei dataa vielä

        if data["status"] in ["failed", "error", "dismissed"]:
            raise RuntimeError(data)

        time.sleep(5)

def fetch_results(job_url):
    results_url = job_url + "/results"

    r = requests.get(results_url, auth=(API_KEY, ""))
    r.raise_for_status()

    return r.json()


def extract_download_url(results_json):
    for item in results_json.get("results", []):
        if "path" in item and item["path"].endswith(".laz"):
            return item["path"]

    raise ValueError("LAZ-latauslinkkiä ei löytynyt")

def calculate_mean_height(download_url):
    print("Ladataan väliaikaiseen tiedostoon...")

    with tempfile.NamedTemporaryFile(suffix=".laz") as tmp:

        r = requests.get(
            download_url,
            auth=(API_KEY, ""),
            stream=True
        )
        r.raise_for_status()

        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                tmp.write(chunk)

        tmp.flush()

        print("Luetaan LAZ...")

        las = laspy.read(tmp.name)

        z = las.z

        mean_height = float(np.mean(z))

        print(f"Pisteitä: {len(z):,}")
        print(f"Keskikorkeus: {mean_height:.2f} m")

        return mean_height


def main():
    job_url = start_job()

    job_url = poll_job(job_url)

    result_json = fetch_results(job_url)

    download_url = extract_download_url(result_json)

    mean_height = calculate_mean_height(download_url)

    print()
    print("Valmis")
    print(f"{MAP_SHEET}: keskimääräinen korkeus = {mean_height:.2f} m")


if __name__ == "__main__":
    main()