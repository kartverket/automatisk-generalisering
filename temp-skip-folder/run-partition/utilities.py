import os

def make_local_output_path(remote_output_path: str) -> str:
    """
    Create a local output path based on the remote output path
    """
    local_output_path = os.path.join("/tmp", os.path.basename(remote_output_path))
    return local_output_path
