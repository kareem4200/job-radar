from job_radar.adapters.ashby import AshbyAdapter
from job_radar.adapters.greenhouse import GreenhouseAdapter
from job_radar.adapters.lever import LeverAdapter
from job_radar.adapters.personio import PersonioAdapter
from job_radar.adapters.smartrecruiters import SmartRecruitersAdapter
from job_radar.adapters.successfactors import SuccessFactorsAdapter
from job_radar.adapters.teamtailor import TeamtailorAdapter
from job_radar.adapters.workday import WorkdayAdapter

ADAPTERS = {
    "greenhouse": GreenhouseAdapter(),
    "personio": PersonioAdapter(),
    "lever": LeverAdapter(),
    "ashby": AshbyAdapter(),
    "teamtailor": TeamtailorAdapter(),
    "smartrecruiters": SmartRecruitersAdapter(),
    "successfactors": SuccessFactorsAdapter(),
    "workday": WorkdayAdapter(),
}