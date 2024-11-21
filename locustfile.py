import time
import uuid
from datetime import datetime

from locust import run_single_user, task, HttpUser, constant
from locust.contrib.fasthttp import ErrorResponse


def convert_to_seconds(time_str):
    time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
    hours = time_obj.hour
    minutes = time_obj.minute
    seconds = time_obj.second
    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds


def get_nested_value(dictionary, keys):
    for key in keys:
        try:
            dictionary = dictionary[key]
        except (KeyError, TypeError):
            return None

    return dictionary

def is_ok(response):
    if isinstance(response, ErrorResponse):
        return False
    print(f"headers: {response.headers}")
    return response.ok


# device simulator that regularly polls and handles config and deployment actions
# inheriting from FastHttpUser can improve perf - but won't support client certificates
class Device(HttpUser):
    host = "http://localhost:60053"

    # initial default - will be overwritten by value returned from goosebit
    wait_time = constant(600)

    cert = None
    # if client certificates are used then reference them here. Noet: single cert for all simulated devices
    # cert = ('001e838c-c68c-4d9d-8417-e2c877c984db.crt', '001e838c-c68c-4d9d-8417-e2c877c984db.key')

    def on_start(self):
        # create device entity
        self.uuid = uuid.uuid4()

    @task
    def poll(self):
        # poll update server
        response = self.client.get(f"/ddi/controller/v1/{self.uuid}", cert=self.cert)
        if not is_ok(response):
            print(f"polling failed {response.status_code}")
            return
        data = response.json()

        # check if config is required
        config_url = get_nested_value(data, ["_links", "configData", "href"])
        if config_url:
            self._register(config_url)

        # check if update is required
        deployment_base = get_nested_value(data, ["_links", "deploymentBase", "href"])
        if deployment_base:
            software_url, software_id = self._retrieve_software_url(deployment_base)
            if software_url is None:
                print("Failed to retrieve software url")
                return

            for i in range(1, 5):
                if not self._feedback(software_id, "none", "proceeding", f"update {i}\nDownloaded {i*10}%\n"):
                    print("Failed to post feedback")
                time.sleep(15)

            # reboot
            time.sleep(120)

            # report finished installation
            if not self._feedback(software_id, "success", "closed"):
                print("Failed to confirm installation")

        sleep = get_nested_value(data, ["config", "polling", "sleep"])
        self.wait_time = lambda: convert_to_seconds(sleep)


    def _register(self, config_url):
        response = self.client.put(
            config_url,
            json={
                "id": "",
                "status": {
                    "result": {"finished": "success"},
                    "execution": "closed",
                    "details": [""],
                },
                "data": {
                    "hw_boardname": "smart-gateway-mt7688",
                    "hw_revision": "1.2.0",
                    "sw_version": "8.8.1-12-g302f635+189128",
                },
            },
           cert = self.cert
        )

        if not is_ok(response):
            print(f"Registration failed {response.status_code}")

    def _retrieve_software_url(self, deployment_base):
        response = self.client.get(deployment_base, cert=self.cert)
        if not is_ok(response):
            print(f"Retrieving update failed {response.status_code}")
            return None, None

        data = response.json()

        first_chunk = get_nested_value(data, ["deployment", "chunks"])[0]
        first_artifact = get_nested_value(first_chunk, ["artifacts"])[0]
        software_url = get_nested_value(first_artifact, ["_links", "download", "href"])
        return software_url, data["id"]

    def _feedback(self, software_id, finished, execution, details=""):
        response = self.client.post(
            f"/ddi/controller/v1/{self.uuid}/deploymentBase/{software_id}/feedback",
            json={
                "id": software_id,
                "status": {
                    "result": {"finished": finished},
                    "execution": execution,
                    "details": [details],
                },
            }, cert=self.cert
        )

        return is_ok(response)


# if launched directly, e.g. "python3 locustfile.py", not "locust -f locustfile.py"
# In PyCharm: activate "Gevent compatible" setting
if __name__ == "__main__":
    run_single_user(Device)
