from job_radar.adapters.ashby import AshbyAdapter
from job_radar.adapters.greenhouse import GreenhouseAdapter
from job_radar.adapters.lever import LeverAdapter
from job_radar.adapters.personio import PersonioAdapter
from job_radar.adapters.teamtailor import TeamtailorAdapter

ADAPTERS = {
    "greenhouse": GreenhouseAdapter(),
    "personio": PersonioAdapter(),
    "lever": LeverAdapter(),
    "ashby": AshbyAdapter(),
    "teamtailor": TeamtailorAdapter(),
}