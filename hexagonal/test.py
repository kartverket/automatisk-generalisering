# Libraries

from .dataValidator import DataValidator

##########################
# Classes
##########################


class Orchestrator:
    def __init__(self, scale: str, feature: str, feature_type: str):
        self.scale = scale
        self.feature = feature
        self.feature_type = feature_type

        self.data_orchestrator = DataOrchestrator(self.scale, self.feature)
        self.data_validator = DataValidator(self.feature, self.feature_type)

    def run(self):
        print("Running orchestrator...")


class DataOrchestrator:
    def __init__(self, scale: str, feature: str):
        self.scale = scale
        self.feature = feature

    def run(self):
        print("Running data orchestrator...")


##########################

if __name__ == "__main__":
    orchestrator = Orchestrator(scale="N100", feature="road", feature_type="polygon")
    orchestrator.run()