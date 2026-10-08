# Libraries

from data_orchestrator_2.names_paths import ObjectType, Scale
from data_orchestrator_2.pipelines import get_pipeline
from data_orchestrator_2.validator import ValidationResult, validate_pipeline

# Constants

INPUT = r"C:\GIS_Files\ag_inputs\raw_data\road.gdb\elveg_and_sti"
OBJECTTYPE = ObjectType.ROAD
SCALE = Scale.N100

# Test

pipeline = get_pipeline(OBJECTTYPE, SCALE)

validation_results: list[ValidationResult] = validate_pipeline(pipeline)
for result in validation_results:
    print(result)
