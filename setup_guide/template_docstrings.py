def docstrings():
    """
    # Summary:
    Finds hospital and church clusters.
    A cluster is defined as two or more points that are closer together than 200 meters.

    # Details:
    - Hospitals are selected based on 'BYGGTYP_NBR' values 970 and 719.
    - Churches are selected based on 'BYGGTYP_NBR' value 671.

    # Parameters
     The tool FindPointClusters have a search distance of 200 meters and minimum points of 2.

    """
