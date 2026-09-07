from job_radar.adapters.greenhouse import GreenhouseAdapter
from job_radar.adapters.lever import LeverAdapter
from job_radar.adapters.personio import PersonioAdapter

ADAPTERS = {
    "greenhouse": GreenhouseAdapter(),
    "personio": PersonioAdapter(),
    "lever": LeverAdapter(),
}
