from enum import Enum


class history_keys(Enum):

    category_history = "category_history"
    accessibility = "accessibility"
    last_processed = "last_processed"
    map_scale = "map_scale"
    operations = "operations"
    order = "order"
    reinserts_completed = "reinserts_completed"
    title = "title"
    newest_version = "newest_version"
    preprocessed = "preprocessed"
    operations_completed = "operations_completed"
    preprocessing_operations_completed = "preprocessing_operations_completed"
    postprocessing_operations_completed = "postprocessing_operations_completed"