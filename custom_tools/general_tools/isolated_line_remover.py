import arcpy
from file_manager.work_file_manager import WorkFileManager
from composition_configs import core_config


class IsolatedLineRemover:
    """
    Remove short isolated line clusters.

    Parameters
    ----------
    input_fc : str
        Path to input line feature class.
    output_gdb : str
        Geodatabase path where result will be written.
    length_threshold : float
        Base length threshold in meters.
    max_lines_per_group : int
        If a cluster has more segments than this, it is kept.
    search_radius_m : float
        Distance in meters to consider features connected.
    length_field : str
        Name of the length field to create/use (default 'seg_length_m').
    """

    def __init__(self,
                 input_fc,
                 output_fc,
                 length_threshold=150.0,
                 length_threshold_add_per_segment=50,
                 max_lines_per_group=5,
                 search_radius_m=10.0,
                 length_field="seg_length_m",
                 ):
        
        self.input_fc = input_fc
        self.output_fc = output_fc
        self.length_threshold = length_threshold
        self.length_threshold_add_per_segment = length_threshold_add_per_segment
        self.max_lines_per_group = max_lines_per_group
        self.search_radius_m = search_radius_m
        self.length_field = length_field
        self.copy_fc = r"in_memory\copy_lines"
        self.near_table = r"in_memory\near_pairs"
        self.layer_name = "lyr_to_delete"


    def copy(self):
        arcpy.management.CopyFeatures(self.input_fc, self.copy_fc)

    def ensure_length_field(self):
        fields = [f.name for f in arcpy.ListFields(self.copy_fc)]
        if self.length_field not in fields:
            arcpy.management.AddField(self.copy_fc, self.length_field, "DOUBLE")
            with arcpy.da.UpdateCursor(self.copy_fc, ["SHAPE@LENGTH", self.length_field]) as ucur:
                for geom_len, _ in ucur:
                    ucur.updateRow([geom_len, geom_len])

    def generate_near_table(self):
        radius_str = f"{self.search_radius_m} Meters"
        arcpy.analysis.GenerateNearTable(in_features=self.copy_fc,
                                         near_features=self.copy_fc,
                                         out_table=self.near_table,
                                         search_radius=radius_str,
                                         location="NO_LOCATION",
                                         angle="NO_ANGLE",
                                         closest="ALL",
                                         method="PLANAR")

    def build_adjacency_and_components(self):
        adjacency = {}
        with arcpy.da.SearchCursor(self.near_table, ["IN_FID", "NEAR_FID"]) as cur:
            for in_fid, near_fid in cur:
                if in_fid == near_fid:
                    continue
                adjacency.setdefault(in_fid, set()).add(near_fid)
                adjacency.setdefault(near_fid, set()).add(in_fid)

        parent = {}
        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        oid_field = arcpy.Describe(self.copy_fc).OIDFieldName
        all_oids = []
        with arcpy.da.SearchCursor(self.copy_fc, [oid_field]) as cur:
            for (oid,) in cur:
                all_oids.append(oid)
                parent.setdefault(oid, oid)

        for a, neighbors in adjacency.items():
            for b in neighbors:
                union(a, b)

        comp_map = {oid: find(oid) for oid in all_oids}
        return comp_map

    def aggregate_by_components(self, comp_map):
        """
        Aggregate lengths and counts by connected component.
        Returns a dict mapping root OID to dict with 'length', 'count', 'members
        """
        totals = {}
        oid_field = arcpy.Describe(self.copy_fc).OIDFieldName
        with arcpy.da.SearchCursor(self.copy_fc, [oid_field, self.length_field]) as cur:
            for oid, seg_len in cur:
                root = comp_map[oid]
                rec = totals.setdefault(root, {"length": 0.0, "count": 0, "members": []})
                rec["length"] += (seg_len or 0.0)
                rec["count"] += 1
                rec["members"].append(oid)
        return totals

    def decide_deletes(self, totals):
        """
        This function adds group to delete list if its below length threshold and below max component count.
        """
        to_delete_oids = []
        for root, rec in totals.items():
            if rec["count"] > self.max_lines_per_group:
                continue
            threshold = self.length_threshold + (self.length_threshold_add_per_segment) * rec["count"]
            if rec["length"] < threshold:
                to_delete_oids.extend(rec["members"])
        return to_delete_oids

    def delete_oids(self, to_delete_oids):
        if not to_delete_oids:
            return 
        
        oid_field = arcpy.Describe(self.copy_fc).OIDFieldName
        arcpy.management.MakeFeatureLayer(self.copy_fc, self.layer_name)
       
        where = f"{arcpy.AddFieldDelimiters(self.copy_fc, oid_field)} IN ({','.join(map(str, to_delete_oids))})"
        arcpy.management.SelectLayerByAttribute(self.layer_name, "NEW_SELECTION", where)
        arcpy.management.DeleteFeatures(self.layer_name)

        arcpy.management.SelectLayerByAttribute(self.layer_name, "CLEAR_SELECTION")
        arcpy.management.Delete(self.layer_name)
        return 

    def run(self):
        """
        Execute the removal process and write output.
        """
        self.copy()
        self.ensure_length_field()

       
        self.generate_near_table()
        comp_map = self.build_adjacency_and_components()
        totals = self.aggregate_by_components(comp_map)
        to_delete_oids = self.decide_deletes(totals)
        self.delete_oids(to_delete_oids)


        arcpy.management.CopyFeatures(self.copy_fc, self.output_fc)

        arcpy.management.Delete(self.copy_fc)
        arcpy.management.Delete(self.near_table)

